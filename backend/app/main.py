"""
Repository Intelligence Platform — FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.routes import documentation, graph, health, query, repositories
from app.core.config import settings
from app.core.logging import setup_logging
from app.embeddings.embedding_service import EmbeddingService
from app.services.cache import CacheService
from app.services.vector_store import VectorStoreService

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Starting Repository Intelligence Platform", version=settings.APP_VERSION)

    # Initialise shared services
    vector_store = VectorStoreService()
    cache = CacheService()

    try:
        await vector_store.initialize()
        await cache.initialize()
    except Exception as e:
        logger.error("Failed to initialise services", error=str(e))
        raise

    app.state.vector_store = vector_store
    app.state.cache = cache

    # Pre-load embedding model in background to warm up
    import asyncio

    embedding_service = EmbeddingService()
    app.state.embedding_service = embedding_service
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, embedding_service._load_model)

    logger.info("Services initialised — ready")
    yield

    logger.info("Shutting down services")
    await cache.close()


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "AI-powered platform for deep repository understanding — semantic search, "
        "AST parsing, dependency graphs, and LLM-driven code intelligence."
    ),
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"https://[a-zA-Z0-9\-]+\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(repositories.router, prefix="/api/v1/repositories", tags=["Repositories"])
app.include_router(query.router, prefix="/api/v1/query", tags=["Query"])
app.include_router(graph.router, prefix="/api/v1/graph", tags=["Graph"])
app.include_router(documentation.router, prefix="/api/v1/documentation", tags=["Documentation"])
