"""Redis cache service for repositories, query results, and graph data."""

from __future__ import annotations

import json
from typing import Any, Optional

import structlog

from app.core.config import settings

logger = structlog.get_logger()


class CacheService:
    """Async Redis cache wrapper."""

    def __init__(self):
        self._redis = None

    async def initialize(self):
        import redis.asyncio as redis_async

        self._redis = redis_async.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
        await self._redis.ping()
        logger.info("Redis connected", url=settings.REDIS_URL)

    async def get(self, key: str) -> Optional[Any]:
        try:
            value = await self._redis.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logger.warning("Cache get failed", key=key, error=str(e))
            return None

    async def set(self, key: str, value: Any, ttl: int = settings.REDIS_TTL) -> bool:
        try:
            await self._redis.set(key, json.dumps(value), ex=ttl)
            return True
        except Exception as e:
            logger.warning("Cache set failed", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        try:
            await self._redis.delete(key)
            return True
        except Exception as e:
            logger.warning("Cache delete failed", key=key, error=str(e))
            return False

    async def delete_pattern(self, pattern: str) -> int:
        try:
            keys = await self._redis.keys(pattern)
            if keys:
                return await self._redis.delete(*keys)
            return 0
        except Exception as e:
            logger.warning("Cache delete_pattern failed", pattern=pattern, error=str(e))
            return 0

    async def exists(self, key: str) -> bool:
        try:
            return bool(await self._redis.exists(key))
        except Exception:
            return False

    async def hset(self, name: str, mapping: dict) -> None:
        try:
            serialized = {k: json.dumps(v) for k, v in mapping.items()}
            await self._redis.hset(name, mapping=serialized)
        except Exception as e:
            logger.warning("Cache hset failed", name=name, error=str(e))

    async def hget(self, name: str, key: str) -> Optional[Any]:
        try:
            value = await self._redis.hget(name, key)
            return json.loads(value) if value else None
        except Exception:
            return None

    async def hgetall(self, name: str) -> dict:
        try:
            raw = await self._redis.hgetall(name)
            return {k: json.loads(v) for k, v in raw.items()}
        except Exception:
            return {}

    async def close(self):
        if self._redis:
            await self._redis.close()

    # ------------------------------------------------------------------
    # Key builders
    # ------------------------------------------------------------------

    @staticmethod
    def repo_key(repo_id: str) -> str:
        return f"repo:{repo_id}"

    @staticmethod
    def repo_list_key() -> str:
        return "repos:all"

    @staticmethod
    def graph_key(repo_id: str) -> str:
        return f"graph:{repo_id}"

    @staticmethod
    def query_key(repo_id: str, question_hash: str) -> str:
        return f"query:{repo_id}:{question_hash}"

    @staticmethod
    def indexing_progress_key(repo_id: str) -> str:
        return f"indexing:{repo_id}:progress"
