"""
Embedding service using BAAI/bge-small-en-v1.5 via sentence-transformers.
Handles batched encoding and caching.
"""
from __future__ import annotations

import hashlib
import json
from typing import List, Optional
import structlog
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.core.config import settings

logger = structlog.get_logger()

_executor = ThreadPoolExecutor(max_workers=2)


class EmbeddingService:
    """Wraps sentence-transformers model for code embedding generation."""

    def __init__(self):
        self._model = None
        self._model_name = settings.EMBEDDING_MODEL
        self._dimension = settings.EMBEDDING_DIMENSION

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading embedding model", model=self._model_name)
            self._model = SentenceTransformer(self._model_name, device="cpu")
            logger.info("Embedding model loaded", dimension=self._dimension)
        return self._model

    def embed_texts_sync(self, texts: List[str]) -> List[List[float]]:
        """Synchronous batch embedding. Runs in calling thread."""
        model = self._load_model()
        embeddings = model.encode(
            texts,
            batch_size=settings.EMBEDDING_BATCH_SIZE,
            show_progress_bar=False,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return embeddings.tolist()

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Async wrapper — runs CPU-heavy encoding in thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, self.embed_texts_sync, texts)

    async def embed_single(self, text: str) -> List[float]:
        results = await self.embed_texts([text])
        return results[0]

    @staticmethod
    def text_hash(text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

    @property
    def dimension(self) -> int:
        return self._dimension
