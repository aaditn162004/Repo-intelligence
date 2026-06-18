"""
Background indexing worker.
Orchestrates the full pipeline: clone → parse → embed → graph → cache.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import structlog
from opentelemetry import trace

from app.core.config import settings
from app.core.telemetry import get_tracer, traced
from app.embeddings.embedding_service import EmbeddingService
from app.graph.knowledge_graph import KnowledgeGraphService
from app.models.code_chunk import CodeChunk
from app.models.repository import IndexingProgress, IndexingStatus, Repository
from app.parsers.ast_parser import ASTParser
from app.parsers.chunker import StructureAwareChunker
from app.parsers.language_detector import detect_frameworks, detect_language, is_supported_language
from app.services.cache import CacheService
from app.services.vector_store import VectorStoreService
from app.utils.file_utils import count_languages, read_file_safe, scan_repository
from app.utils.git_utils import cleanup_repository, clone_repository, extract_repo_name
from app.utils.zip_utils import extract_zip, validate_zip

logger = structlog.get_logger()
tracer = get_tracer("repointel.indexing")


class IndexingWorker:
    """Executes the full repository indexing pipeline."""

    def __init__(
        self,
        vector_store: VectorStoreService,
        embedding_service: EmbeddingService,
        knowledge_graph: KnowledgeGraphService,
        cache: CacheService,
    ):
        self._vector_store = vector_store
        self._embedder = embedding_service
        self._kg = knowledge_graph
        self._cache = cache
        self._ast_parser = ASTParser()
        self._chunker = StructureAwareChunker()

    async def index_github_repo(
        self, repository: Repository, github_token: Optional[str] = None
    ) -> Repository:
        return await self._run_pipeline(repository, source="github", github_token=github_token)

    async def index_zip_repo(self, repository: Repository, zip_path: str) -> Repository:
        return await self._run_pipeline(repository, source="zip", zip_path=zip_path)

    @traced("index.pipeline")
    async def _run_pipeline(
        self,
        repo: Repository,
        source: str,
        github_token: Optional[str] = None,
        zip_path: Optional[str] = None,
    ) -> Repository:
        repo_dir = os.path.join(settings.repos_dir, repo.id)

        try:
            # --- Stage 1: Clone / extract ---
            await self._update_progress(repo.id, IndexingStatus.CLONING, "Cloning repository", 5)

            with tracer.start_as_current_span("index.fetch") as span:
                span.set_attribute("index.source", source)
                if source == "github":
                    repo_path = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: clone_repository(repo.url, repo_dir, repo.branch, github_token),
                    )
                else:
                    repo_path = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: extract_zip(zip_path, repo_dir)
                    )

            # --- Stage 2: Scan files ---
            await self._update_progress(repo.id, IndexingStatus.PARSING, "Scanning files", 15)
            file_list = scan_repository(repo_path)
            lang_counts = count_languages(file_list)

            repo.total_files = len(file_list)
            repo.languages = list(lang_counts.keys())
            repo.primary_language = max(lang_counts, key=lang_counts.get) if lang_counts else None

            # --- Stage 3: Parse and chunk ---
            all_chunks: List[CodeChunk] = []
            framework_hints: set = set()

            for i, (abs_path, rel_path) in enumerate(file_list):
                lang = detect_language(rel_path)
                content = read_file_safe(abs_path)
                if not content:
                    continue

                # Detect frameworks from content
                hints = detect_frameworks(content[:2000])
                framework_hints.update(hints)

                if is_supported_language(lang):
                    chunks = self._ast_parser.parse_file(rel_path, content, lang, repo.id)
                    all_chunks.extend(chunks)
                else:
                    # For unsupported languages, add a single module chunk
                    from app.models.code_chunk import ChunkType

                    all_chunks.append(
                        CodeChunk(
                            repository_id=repo.id,
                            file_path=rel_path,
                            language=lang or "unknown",
                            chunk_type=ChunkType.MODULE,
                            name=Path(rel_path).stem,
                            content=content[:1500],
                            start_line=1,
                            end_line=len(content.splitlines()),
                        )
                    )

                if i % 20 == 0:
                    progress = 15 + (i / len(file_list)) * 30
                    await self._update_progress(
                        repo.id,
                        IndexingStatus.PARSING,
                        f"Parsing {rel_path}",
                        progress,
                        current_file=rel_path,
                        indexed_files=i,
                        total_files=len(file_list),
                    )

            repo.framework_hints = list(framework_hints)
            repo.total_chunks = len(all_chunks)
            pipeline_span = trace.get_current_span()
            pipeline_span.set_attribute("index.total_files", len(file_list))
            pipeline_span.set_attribute("index.total_chunks", len(all_chunks))

            # --- Stage 4: Create Qdrant collection ---
            await self._update_progress(
                repo.id, IndexingStatus.EMBEDDING, "Creating vector index", 50
            )
            with tracer.start_as_current_span("index.create_collection"):
                await self._vector_store.create_collection(repo.id)

            # --- Stage 5: Embed chunks in batches ---
            embedding_items = self._chunker.prepare_for_embedding(all_chunks)
            texts = [item["text"] for item in embedding_items]
            chunks_to_embed = [item["chunk"] for item in embedding_items]

            batch_size = settings.EMBEDDING_BATCH_SIZE
            for batch_start in range(0, len(texts), batch_size):
                batch_texts = texts[batch_start : batch_start + batch_size]
                batch_chunks = chunks_to_embed[batch_start : batch_start + batch_size]

                with tracer.start_as_current_span("index.embed_batch") as span:
                    span.set_attribute("batch.size", len(batch_texts))
                    embeddings = await self._embedder.embed_texts(batch_texts)
                    await self._vector_store.upsert_chunks(
                        repo.id, batch_chunks, embeddings, batch_texts
                    )

                progress = 50 + (batch_start / max(len(texts), 1)) * 30
                await self._update_progress(
                    repo.id,
                    IndexingStatus.EMBEDDING,
                    f"Embedding chunks {batch_start}/{len(texts)}",
                    progress,
                )

            # --- Stage 6: Build knowledge graph ---
            await self._update_progress(
                repo.id, IndexingStatus.GRAPHING, "Building dependency graph", 85
            )
            with tracer.start_as_current_span("index.build_graph") as span:
                span.set_attribute("index.chunks", len(all_chunks))
                await self._kg.build_graph(repo.id, all_chunks)

            # --- Stage 7: Finalize ---
            repo.status = IndexingStatus.READY
            repo.indexed_files = len(file_list)
            repo.indexed_at = datetime.utcnow()
            repo.updated_at = datetime.utcnow()

            await self._update_progress(repo.id, IndexingStatus.READY, "Indexing complete", 100)

            # Cache the repository metadata
            await self._cache.set(CacheService.repo_key(repo.id), repo.model_dump(mode="json"))
            logger.info("Repository indexed", repo_id=repo.id, chunks=len(all_chunks))

        except Exception as e:
            logger.exception("Indexing failed", repo_id=repo.id, error=str(e))
            repo.status = IndexingStatus.FAILED
            repo.error_message = str(e)
            await self._update_progress(repo.id, IndexingStatus.FAILED, f"Error: {e}", 0)
            await self._cache.set(CacheService.repo_key(repo.id), repo.model_dump(mode="json"))
        finally:
            if source == "github" and os.path.exists(repo_dir):
                cleanup_repository(repo_dir)

        return repo

    async def _update_progress(
        self,
        repo_id: str,
        status: IndexingStatus,
        message: str,
        progress: float,
        current_file: Optional[str] = None,
        indexed_files: int = 0,
        total_files: int = 0,
    ) -> None:
        progress_data = IndexingProgress(
            repository_id=repo_id,
            status=status,
            stage=message,
            progress=min(progress, 100.0),
            current_file=current_file,
            message=message,
            indexed_files=indexed_files,
            total_files=total_files,
        )
        await self._cache.set(
            CacheService.indexing_progress_key(repo_id),
            progress_data.model_dump(mode="json"),
            ttl=3600,
        )
