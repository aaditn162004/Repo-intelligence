"""
Qdrant vector store service.
Manages collections per repository and handles hybrid retrieval.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import structlog

from app.core.config import settings
from app.models.code_chunk import CodeChunk

logger = structlog.get_logger()


class VectorStoreService:
    """Manages Qdrant vector collections for repository code chunks."""

    def __init__(self):
        self._client = None

    async def initialize(self):
        from qdrant_client import QdrantClient

        if settings.QDRANT_URL:
            self._client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY or None,
                timeout=30,
            )
            logger.info("Qdrant connected (cloud)", url=settings.QDRANT_URL)
        else:
            self._client = QdrantClient(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT,
                timeout=30,
            )
            logger.info(
                "Qdrant connected (local)", host=settings.QDRANT_HOST, port=settings.QDRANT_PORT
            )

    def _collection_name(self, repository_id: str) -> str:
        safe_id = repository_id.replace("-", "_")[:32]
        return f"{settings.QDRANT_COLLECTION_PREFIX}_{safe_id}"

    async def create_collection(self, repository_id: str) -> None:
        from qdrant_client.models import Distance, VectorParams

        collection_name = self._collection_name(repository_id)
        existing = [c.name for c in self._client.get_collections().collections]

        if collection_name not in existing:
            self._client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=settings.EMBEDDING_DIMENSION,
                    distance=Distance.COSINE,
                ),
            )
            logger.info("Created Qdrant collection", collection=collection_name)

    async def upsert_chunks(
        self,
        repository_id: str,
        chunks: List[CodeChunk],
        embeddings: List[List[float]],
        texts: List[str],
    ) -> None:
        from qdrant_client.models import PointStruct

        collection_name = self._collection_name(repository_id)
        points = []

        for chunk, embedding, text in zip(chunks, embeddings, texts):
            payload = {
                "chunk_id": chunk.id,
                "repository_id": chunk.repository_id,
                "file_path": chunk.file_path,
                "language": chunk.language,
                "chunk_type": chunk.chunk_type,
                "name": chunk.name or "",
                "parent_name": chunk.parent_name or "",
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "signature": chunk.signature or "",
                "docstring": chunk.docstring or "",
                "decorators": chunk.decorators,
                "content": chunk.content[:1000],
                "text_for_search": text[:500],
            }
            points.append(
                PointStruct(
                    id=self._chunk_id_to_int(chunk.id),
                    vector=embedding,
                    payload=payload,
                )
            )

        # Batch upsert
        batch_size = 100
        for i in range(0, len(points), batch_size):
            self._client.upsert(
                collection_name=collection_name,
                points=points[i : i + batch_size],
            )

        logger.info("Upserted chunks", collection=collection_name, count=len(points))

    async def search(
        self,
        repository_id: str,
        query_embedding: List[float],
        top_k: int = 10,
        score_threshold: float = 0.0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        collection_name = self._collection_name(repository_id)

        qdrant_filter = None
        if filters:
            conditions = []
            for key, value in filters.items():
                conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
            if conditions:
                qdrant_filter = Filter(must=conditions)

        results = self._client.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=top_k,
            score_threshold=score_threshold,
            query_filter=qdrant_filter,
            with_payload=True,
        )

        return [
            {
                "score": hit.score,
                "payload": hit.payload,
                "id": hit.id,
            }
            for hit in results
        ]

    async def delete_collection(self, repository_id: str) -> None:
        collection_name = self._collection_name(repository_id)
        try:
            self._client.delete_collection(collection_name)
            logger.info("Deleted collection", collection=collection_name)
        except Exception as e:
            logger.warning("Failed to delete collection", error=str(e))

    async def get_collection_info(self, repository_id: str) -> Dict[str, Any]:
        collection_name = self._collection_name(repository_id)
        try:
            info = self._client.get_collection(collection_name)
            return {
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status,
            }
        except Exception:
            return {"vectors_count": 0, "points_count": 0, "status": "not_found"}

    @staticmethod
    def _chunk_id_to_int(chunk_id: str) -> int:
        import hashlib

        return int(hashlib.md5(chunk_id.encode()).hexdigest()[:15], 16)
