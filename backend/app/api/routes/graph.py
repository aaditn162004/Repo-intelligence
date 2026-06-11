"""Dependency graph and architecture visualisation endpoints."""

from __future__ import annotations

from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException, Query, Request

from app.models.repository import IndexingStatus, Repository
from app.services.cache import CacheService

logger = structlog.get_logger()
router = APIRouter()


def _get_kg_service(request: Request):
    from app.graph.knowledge_graph import KnowledgeGraphService

    return KnowledgeGraphService(request.app.state.cache)


@router.get("/{repo_id}/full")
async def get_full_graph(repo_id: str, request: Request):
    cache: CacheService = request.app.state.cache
    graph_data = await cache.get(CacheService.graph_key(repo_id))
    if not graph_data:
        raise HTTPException(404, "Graph not found — repository may not be indexed yet")
    return graph_data


@router.get("/{repo_id}/subgraph")
async def get_subgraph(
    repo_id: str,
    request: Request,
    file_path: str = Query(..., description="File path to centre the subgraph on"),
    depth: int = Query(default=2, ge=1, le=4),
):
    kg = _get_kg_service(request)
    return await kg.get_subgraph(repo_id, file_path, depth=depth)


@router.get("/{repo_id}/affected")
async def get_affected_files(
    repo_id: str,
    request: Request,
    file_path: str = Query(..., description="File that was changed"),
):
    kg = _get_kg_service(request)
    affected = await kg.get_affected_files(repo_id, file_path)
    return {"file_path": file_path, "affected_files": affected}


@router.get("/{repo_id}/architecture")
async def get_architecture_summary(repo_id: str, request: Request):
    """High-level architecture stats — total nodes, most connected files, etc."""
    kg = _get_kg_service(request)
    return await kg.get_architecture_summary(repo_id)
