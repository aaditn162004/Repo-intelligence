"""Documentation generation endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse
import structlog

from app.models.query import DocumentationRequest, DocumentationResponse
from app.models.repository import Repository, IndexingStatus
from app.services.cache import CacheService
from app.embeddings.embedding_service import EmbeddingService
from app.retrieval.hybrid_retriever import HybridRetriever
from app.retrieval.context_builder import ContextBuilder

logger = structlog.get_logger()
router = APIRouter()

_embedding_service = EmbeddingService()


@router.post("/generate", response_model=DocumentationResponse)
async def generate_documentation(doc_req: DocumentationRequest, request: Request):
    """Generate AI documentation for a module, function, API, or the full architecture."""
    cache: CacheService = request.app.state.cache

    repo_data = await cache.get(CacheService.repo_key(doc_req.repository_id))
    if not repo_data:
        raise HTTPException(404, "Repository not found")

    repo = Repository(**repo_data)
    if repo.status != IndexingStatus.READY:
        raise HTTPException(400, "Repository not ready")

    from app.graph.knowledge_graph import KnowledgeGraphService
    kg = KnowledgeGraphService(cache)
    retriever = HybridRetriever(request.app.state.vector_store, _embedding_service, kg)
    context_builder = ContextBuilder()

    # Build retrieval query
    doc_query = f"documentation for {doc_req.target} {doc_req.doc_type}"
    retrieval_result = await retriever.retrieve(doc_req.repository_id, doc_query, top_k=8)
    context_text = context_builder.build_context(
        retrieval_result["sources"], retrieval_result.get("graph_context", {})
    )

    # Generate with LLM
    from langchain_ollama import ChatOllama
    from langchain_core.messages import SystemMessage, HumanMessage
    from app.core.config import settings

    llm = ChatOllama(
        model=settings.LLM_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=0.2,
        num_predict=2048,
    )

    system = (
        f"You are an expert technical writer generating {doc_req.doc_type} documentation.\n"
        "Use the provided code context to generate accurate, comprehensive documentation.\n"
        "Format: Markdown. Include purpose, parameters, return values, examples, edge cases."
    )
    prompt = f"Generate {doc_req.doc_type} documentation for: {doc_req.target}\n\n{context_text}"

    response = llm.invoke([SystemMessage(content=system), HumanMessage(content=prompt)])

    return DocumentationResponse(
        repository_id=doc_req.repository_id,
        target=doc_req.target,
        doc_type=doc_req.doc_type,
        content=response.content,
        format=doc_req.format,
    )


@router.get("/{repo_id}/readme")
async def generate_readme(repo_id: str, request: Request):
    """Generate a README.md for the repository."""
    cache: CacheService = request.app.state.cache
    repo_data = await cache.get(CacheService.repo_key(repo_id))
    if not repo_data:
        raise HTTPException(404, "Repository not found")

    repo = Repository(**repo_data)
    if repo.status != IndexingStatus.READY:
        raise HTTPException(400, "Repository not ready")

    from app.graph.knowledge_graph import KnowledgeGraphService
    from langchain_ollama import ChatOllama
    from langchain_core.messages import SystemMessage, HumanMessage
    from app.core.config import settings

    kg = KnowledgeGraphService(cache)
    arch_summary = await kg.get_architecture_summary(repo_id)

    llm = ChatOllama(
        model=settings.LLM_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=0.3,
        num_predict=3000,
    )

    system = "You are a developer advocate writing a professional README.md for an open-source project."
    prompt = (
        f"Generate a professional README.md for the repository: **{repo.name}**\n\n"
        f"Repository stats:\n"
        f"- Languages: {', '.join(repo.languages)}\n"
        f"- Primary language: {repo.primary_language}\n"
        f"- Frameworks detected: {', '.join(repo.framework_hints)}\n"
        f"- Total files: {repo.total_files}\n"
        f"- Architecture: {arch_summary}\n\n"
        "Include: description, features, installation, usage, architecture overview, contributing guide."
    )
    response = llm.invoke([SystemMessage(content=system), HumanMessage(content=prompt)])
    return PlainTextResponse(response.content, media_type="text/markdown")
