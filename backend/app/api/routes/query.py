"""Natural language query endpoints with streaming SSE support."""

from __future__ import annotations

import hashlib
import json
from typing import AsyncIterator

import structlog
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.agents.orchestrator import RepoAgentGraph
from app.embeddings.embedding_service import EmbeddingService
from app.models.query import QueryRequest, QueryResponse, QueryType
from app.models.repository import IndexingStatus, Repository
from app.retrieval.hybrid_retriever import HybridRetriever
from app.services.cache import CacheService

logger = structlog.get_logger()
router = APIRouter()

_embedding_service = EmbeddingService()


def _get_agent_graph(request: Request) -> RepoAgentGraph:
    from app.graph.knowledge_graph import KnowledgeGraphService

    cache = request.app.state.cache
    vector_store = request.app.state.vector_store

    kg = KnowledgeGraphService(cache)
    retriever = HybridRetriever(vector_store, _embedding_service, kg)
    return RepoAgentGraph(retriever, kg)


@router.post("/stream")
async def stream_query(query_req: QueryRequest, request: Request):
    """Stream an AI-generated answer as Server-Sent Events."""
    cache: CacheService = request.app.state.cache

    repo_data = await cache.get(CacheService.repo_key(query_req.repository_id))
    if not repo_data:
        raise HTTPException(404, "Repository not found")

    repo = Repository(**repo_data)
    if repo.status != IndexingStatus.READY:
        raise HTTPException(400, f"Repository not ready (status: {repo.status})")

    agent_graph = _get_agent_graph(request)

    async def event_generator() -> AsyncIterator[str]:
        try:
            async for chunk in agent_graph.stream(
                repository_id=repo.id,
                repository_name=repo.name,
                question=query_req.question,
                top_k=query_req.max_context_chunks,
            ):
                yield f"data: {chunk}\n\n"
        except Exception as e:
            logger.exception("Streaming query failed", error=str(e))
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("", response_model=QueryResponse)
async def query_repository(query_req: QueryRequest, request: Request):
    """Non-streaming query — waits for full response."""
    cache: CacheService = request.app.state.cache

    repo_data = await cache.get(CacheService.repo_key(query_req.repository_id))
    if not repo_data:
        raise HTTPException(404, "Repository not found")

    repo = Repository(**repo_data)
    if repo.status != IndexingStatus.READY:
        raise HTTPException(400, f"Repository not ready (status: {repo.status})")

    # Cache key based on question content
    q_hash = hashlib.md5(query_req.question.encode()).hexdigest()
    cache_key = CacheService.query_key(repo.id, q_hash)
    cached = await cache.get(cache_key)
    if cached:
        return QueryResponse(**cached)

    agent_graph = _get_agent_graph(request)
    result = await agent_graph.run(
        repository_id=repo.id,
        repository_name=repo.name,
        question=query_req.question,
        top_k=query_req.max_context_chunks,
    )

    response = QueryResponse(
        repository_id=repo.id,
        question=query_req.question,
        answer=result["answer"],
        query_type=QueryType(result["query_type"]),
        sources=result["sources"],
        graph_context=result.get("graph_context"),
        reasoning_steps=result.get("reasoning_steps", []),
    )

    # Cache for 10 minutes
    await cache.set(cache_key, response.model_dump(mode="json"), ttl=600)
    return response
