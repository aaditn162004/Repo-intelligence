"""
Hybrid retriever: combines semantic vector search with graph-aware context.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import structlog

from app.core.config import settings
from app.embeddings.embedding_service import EmbeddingService
from app.graph.knowledge_graph import KnowledgeGraphService
from app.models.query import SourceReference
from app.services.vector_store import VectorStoreService

logger = structlog.get_logger()


class HybridRetriever:

    def __init__(
        self,
        vector_store: VectorStoreService,
        embedding_service: EmbeddingService,
        knowledge_graph: KnowledgeGraphService,
    ):
        self._vector_store = vector_store
        self._embedder = embedding_service
        self._kg = knowledge_graph

    async def retrieve(
        self,
        repository_id: str,
        query: str,
        top_k: int = settings.TOP_K_RESULTS,
        include_graph: bool = True,
        chunk_type_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Main retrieval entry point.
        Returns semantic hits + graph-expanded context.
        """
        # 1. Embed the query
        query_embedding = await self._embedder.embed_single(query)

        # 2. Semantic search
        filters = {"chunk_type": chunk_type_filter} if chunk_type_filter else None
        hits = await self._vector_store.search(
            repository_id=repository_id,
            query_embedding=query_embedding,
            top_k=top_k,
            score_threshold=settings.SIMILARITY_THRESHOLD,
            filters=filters,
        )

        # 3. Optionally expand with graph context
        graph_context: Dict[str, Any] = {}
        expanded_hits: List[Dict[str, Any]] = list(hits)

        if include_graph and hits:
            graph_context = await self._expand_with_graph(repository_id, hits)

        # 4. Deduplicate and rank
        ranked_hits = self._rank_hits(expanded_hits)

        # 5. Build source references
        sources = self._build_source_references(ranked_hits)

        return {
            "sources": sources,
            "graph_context": graph_context,
            "raw_hits": ranked_hits[:top_k],
        }

    async def _expand_with_graph(
        self, repository_id: str, hits: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Expand retrieval context using the dependency graph."""
        affected_files: set = set()
        related_files: set = set()

        for hit in hits[:5]:  # Only expand top-5
            file_path = hit["payload"].get("file_path", "")
            if file_path:
                affected = await self._kg.get_affected_files(repository_id, file_path)
                affected_files.update(affected)
                subgraph = await self._kg.get_subgraph(repository_id, file_path, depth=1)
                for node in subgraph.get("nodes", []):
                    fp = node.get("file_path", "")
                    if fp:
                        related_files.add(fp)

        return {
            "affected_files": list(affected_files)[:10],
            "related_files": list(related_files)[:10],
        }

    def _rank_hits(self, hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Re-rank hits: boost functions/classes over imports/modules."""
        type_boost = {
            "function": 1.2,
            "method": 1.15,
            "class": 1.1,
            "route": 1.25,
            "module": 0.9,
            "import": 0.7,
            "snippet": 0.8,
        }
        for hit in hits:
            chunk_type = hit["payload"].get("chunk_type", "snippet")
            boost = type_boost.get(chunk_type, 1.0)
            hit["final_score"] = hit["score"] * boost

        return sorted(hits, key=lambda h: h.get("final_score", h["score"]), reverse=True)

    @staticmethod
    def _build_source_references(hits: List[Dict[str, Any]]) -> List[SourceReference]:
        refs = []
        for hit in hits:
            p = hit["payload"]
            refs.append(
                SourceReference(
                    chunk_id=p.get("chunk_id", ""),
                    file_path=p.get("file_path", ""),
                    chunk_type=p.get("chunk_type", "snippet"),
                    name=p.get("name") or None,
                    start_line=p.get("start_line", 0),
                    end_line=p.get("end_line", 0),
                    relevance_score=round(hit.get("final_score", hit["score"]), 4),
                    snippet=p.get("content", "")[:300],
                )
            )
        return refs
