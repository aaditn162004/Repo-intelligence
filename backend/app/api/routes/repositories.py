"""Repository CRUD and ingestion endpoints."""

from __future__ import annotations

import asyncio
import os
import tempfile
import uuid
from datetime import datetime
from typing import List, Optional

import structlog
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from app.models.repository import IndexingProgress, IndexingStatus, Repository, RepositoryCreate
from app.services.cache import CacheService
from app.utils.git_utils import extract_repo_name

logger = structlog.get_logger()
router = APIRouter()


def _get_services(request: Request):
    return request.app.state.vector_store, request.app.state.cache


# ---------------------------------------------------------------------------
# Background indexing launcher
# ---------------------------------------------------------------------------


async def _launch_indexing(app_state, repo: Repository, zip_path: Optional[str] = None):
    from app.core.config import settings
    from app.embeddings.embedding_service import EmbeddingService
    from app.graph.knowledge_graph import KnowledgeGraphService
    from app.workers.indexing_worker import IndexingWorker

    embedding_service = EmbeddingService()
    kg_service = KnowledgeGraphService(app_state.cache)
    worker = IndexingWorker(
        vector_store=app_state.vector_store,
        embedding_service=embedding_service,
        knowledge_graph=kg_service,
        cache=app_state.cache,
    )

    if zip_path:
        await worker.index_zip_repo(repo, zip_path)
    else:
        await worker.index_github_repo(repo, github_token=settings.GITHUB_TOKEN or None)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", response_model=Repository, status_code=202)
async def create_repository(
    repo_create: RepositoryCreate,
    background_tasks: BackgroundTasks,
    request: Request,
):
    """Ingest a GitHub repository URL and start background indexing."""
    cache: CacheService = request.app.state.cache

    repo_name = repo_create.name or extract_repo_name(repo_create.url)
    repo = Repository(
        name=repo_name,
        url=repo_create.url,
        branch=repo_create.branch,
        status=IndexingStatus.PENDING,
    )

    # Persist immediately so the UI can track status
    await cache.set(CacheService.repo_key(repo.id), repo.model_dump(mode="json"))

    # Add to repo list
    repo_list = await cache.get(CacheService.repo_list_key()) or []
    repo_list.append(repo.id)
    await cache.set(CacheService.repo_list_key(), repo_list, ttl=0)  # no expiry

    background_tasks.add_task(_launch_indexing, request.app.state, repo)
    logger.info("Repository ingestion started", repo_id=repo.id, url=repo.url)
    return repo


@router.post("/upload", response_model=Repository, status_code=202)
async def upload_repository(
    background_tasks: BackgroundTasks,
    request: Request,
    file: UploadFile = File(...),
    name: str = Form(...),
):
    """Upload a ZIP archive of a repository and start background indexing."""
    if not file.filename.endswith(".zip"):
        raise HTTPException(400, "Only ZIP archives are supported")

    cache: CacheService = request.app.state.cache
    repo = Repository(name=name, url="", status=IndexingStatus.PENDING)

    # Save ZIP to temp file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    content = await file.read()
    tmp.write(content)
    tmp.close()

    await cache.set(CacheService.repo_key(repo.id), repo.model_dump(mode="json"))
    repo_list = await cache.get(CacheService.repo_list_key()) or []
    repo_list.append(repo.id)
    await cache.set(CacheService.repo_list_key(), repo_list, ttl=0)

    background_tasks.add_task(_launch_indexing, request.app.state, repo, tmp.name)
    return repo


@router.get("", response_model=List[Repository])
async def list_repositories(request: Request):
    cache: CacheService = request.app.state.cache
    repo_ids = await cache.get(CacheService.repo_list_key()) or []

    repos = []
    for rid in repo_ids:
        data = await cache.get(CacheService.repo_key(rid))
        if data:
            repos.append(Repository(**data))
    return repos


@router.get("/{repo_id}", response_model=Repository)
async def get_repository(repo_id: str, request: Request):
    cache: CacheService = request.app.state.cache
    data = await cache.get(CacheService.repo_key(repo_id))
    if not data:
        raise HTTPException(404, "Repository not found")
    return Repository(**data)


@router.delete("/{repo_id}", status_code=204)
async def delete_repository(repo_id: str, request: Request):
    cache: CacheService = request.app.state.cache
    vector_store = request.app.state.vector_store

    # Delete vectors
    await vector_store.delete_collection(repo_id)

    # Remove from cache
    await cache.delete(CacheService.repo_key(repo_id))
    await cache.delete(CacheService.graph_key(repo_id))

    # Remove from list
    repo_list = await cache.get(CacheService.repo_list_key()) or []
    repo_list = [r for r in repo_list if r != repo_id]
    await cache.set(CacheService.repo_list_key(), repo_list, ttl=0)


@router.get("/{repo_id}/progress", response_model=IndexingProgress)
async def get_indexing_progress(repo_id: str, request: Request):
    cache: CacheService = request.app.state.cache
    data = await cache.get(CacheService.indexing_progress_key(repo_id))
    if not data:
        raise HTTPException(404, "No progress info for this repository")
    return IndexingProgress(**data)


@router.post("/{repo_id}/reindex", response_model=Repository, status_code=202)
async def reindex_repository(
    repo_id: str,
    background_tasks: BackgroundTasks,
    request: Request,
):
    cache: CacheService = request.app.state.cache
    data = await cache.get(CacheService.repo_key(repo_id))
    if not data:
        raise HTTPException(404, "Repository not found")

    repo = Repository(**data)
    repo.status = IndexingStatus.PENDING
    repo.indexed_at = None
    repo.error_message = None
    await cache.set(CacheService.repo_key(repo_id), repo.model_dump(mode="json"))

    background_tasks.add_task(_launch_indexing, request.app.state, repo)
    return repo
