"""
High-level knowledge graph service.
Wraps DependencyGraph with serialisation/caching via Redis.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import structlog

from app.graph.dependency_graph import DependencyGraph
from app.models.code_chunk import CodeChunk
from app.services.cache import CacheService

logger = structlog.get_logger()


class KnowledgeGraphService:

    def __init__(self, cache: CacheService):
        self._cache = cache
        self._graphs: Dict[str, DependencyGraph] = {}

    async def build_graph(self, repository_id: str, chunks: List[CodeChunk]) -> DependencyGraph:
        graph = DependencyGraph(repository_id)
        graph.build_from_chunks(chunks)
        self._graphs[repository_id] = graph

        # Persist serialised version to Redis
        graph_data = graph.to_dict()
        await self._cache.set(
            CacheService.graph_key(repository_id),
            graph_data,
            ttl=86400,  # 24 h
        )
        logger.info("Knowledge graph cached", repository_id=repository_id)
        return graph

    async def get_graph(self, repository_id: str) -> Optional[DependencyGraph]:
        if repository_id in self._graphs:
            return self._graphs[repository_id]
        return None

    async def get_graph_data(self, repository_id: str) -> Optional[Dict[str, Any]]:
        """Return serialised graph dict (from cache or in-memory)."""
        if repository_id in self._graphs:
            return self._graphs[repository_id].to_dict()

        cached = await self._cache.get(CacheService.graph_key(repository_id))
        return cached

    async def get_subgraph(
        self, repository_id: str, file_path: str, depth: int = 2
    ) -> Dict[str, Any]:
        graph = await self.get_graph(repository_id)
        if graph is None:
            return {"nodes": [], "edges": []}
        return graph.get_subgraph(file_path, depth=depth)

    async def get_affected_files(self, repository_id: str, file_path: str) -> List[str]:
        graph = await self.get_graph(repository_id)
        if graph is None:
            return []
        return graph.get_affected_files(file_path)

    async def get_architecture_summary(self, repository_id: str) -> Dict[str, Any]:
        graph = await self.get_graph(repository_id)
        if graph is None:
            return {}

        g = graph.graph
        type_counts: Dict[str, int] = {}
        for _, attrs in g.nodes(data=True):
            t = attrs.get("type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1

        top_files = sorted(
            [(n, g.degree(n)) for n in g.nodes if g.nodes[n].get("type") == "file"],
            key=lambda x: x[1],
            reverse=True,
        )[:10]

        return {
            "total_nodes": g.number_of_nodes(),
            "total_edges": g.number_of_edges(),
            "node_types": type_counts,
            "most_connected_files": [{"file": f, "connections": d} for f, d in top_files],
        }
