# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

RepoIntel — index any GitHub repo (or uploaded ZIP), then answer natural-language questions about it using AST-aware retrieval, a dependency graph, and a LangGraph multi-agent pipeline. Python/FastAPI backend + Next.js 15 frontend, in one repo.

## Commands

Backend (`cd backend`):
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

# infra only (Qdrant + Redis + Ollama) so you can run the app on the host
docker compose up qdrant redis ollama -d
docker exec repo_intel_ollama ollama pull qwen2.5-coder:7b   # local LLM

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pytest tests/ -v                       # all tests
pytest tests/test_parsers.py -v        # one file
pytest tests/test_api.py::test_name    # one test (asyncio_mode=auto, no decorator needed)

ruff check app/        # lint  (CI runs this; line-length 100)
black --check app/     # format (CI runs this; drop --check to apply)
```

Frontend (`cd frontend`):
```bash
npm install
npm run dev          # http://localhost:3000
npm run type-check   # tsc --noEmit — CI gate
npm run lint         # eslint  — CI gate
npm run build        # needs NEXT_PUBLIC_API_URL set (baked in at build time)
```

Full stack: `docker compose up -d` (root) starts everything incl. frontend on :3000, backend on :8000. `docker-compose.dev.yml` is a hot-reload override.

## Architecture — what you need to read multiple files to learn

**There is no database.** Redis is the source of truth for all runtime state: repository metadata, indexing progress, query-result cache, and the serialized dependency graph. All keys are built by the `CacheService.*_key()` static methods in [backend/app/services/cache.py](backend/app/services/cache.py) — use them, don't hand-write key strings. Qdrant holds only vectors (one collection per repo, prefix `repo_intel`).

**Indexing pipeline** ([backend/app/workers/indexing_worker.py](backend/app/workers/indexing_worker.py)) runs as a FastAPI background task and is the spine of the system: clone/extract → scan → AST-parse & chunk (`parsers/`) → embed in batches → upsert to Qdrant → build dependency graph → cache metadata. It writes progress to Redis at every stage; the frontend polls `/repositories/{id}/progress`. GitHub clones are cleaned up from disk after indexing; ZIP extracts are not.

**Retrieval is hybrid** ([backend/app/retrieval/hybrid_retriever.py](backend/app/retrieval/hybrid_retriever.py)): semantic vector search, then graph expansion of the top-5 hits (affected + related files via the dependency graph), then a chunk-type re-rank that boosts `route`/`function`/`method`/`class` over `import`/`module`. The re-ranked sources feed the context builder.

**Multi-agent answer flow** ([backend/app/agents/orchestrator.py](backend/app/agents/orchestrator.py)): LangGraph `planner → {architect | documenter | impact_analyzer} → synthesizer → END`. The planner is an LLM call that classifies the query into a `QueryType`; `route_after_planner` maps that to the specialist node (anything unrecognized goes straight to `synthesizer`). Retrieval happens **outside** the graph in `RepoAgentGraph.run`/`.stream` and is injected as `context_text` — the `retriever_node` in the graph is only a placeholder.

**LLM provider is swappable via `settings.LLM_PROVIDER`** (`ollama` local default, `groq` cloud). `_get_llm()` in the orchestrator is the single switch point. Important streaming detail: for Ollama the `.stream()` path bypasses LangChain and calls the Ollama REST `/api/chat` directly with `httpx`, because LangChain buffers tokens; Groq streams natively via `astream`. If you touch streaming, preserve this split.

**Streaming wire format**: backend emits SSE (`data: {json}\n\n`) with token objects `{type: "metadata"|"token"|"done"|"error"}`. The frontend hook [frontend/src/hooks/useStreamingQuery.ts](frontend/src/hooks/useStreamingQuery.ts) parses these and deliberately *re-paces* tokens through a drip queue (~33 tok/s) for smooth rendering rather than dumping them as they arrive.

**Frontend ↔ backend**: every call goes through the typed `api` object in [frontend/src/lib/api.ts](frontend/src/lib/api.ts); base URL is `NEXT_PUBLIC_API_URL` + `/api/v1` (falls back to a same-origin `/api/v1` proxy). Add new endpoints there, keep types in [frontend/src/types/index.ts](frontend/src/types/index.ts) in sync with the Pydantic models in `backend/app/models/`. Routers are mounted in [backend/app/main.py](backend/app/main.py).

## Observability (OpenTelemetry)

Tracing is set up in [backend/app/core/telemetry.py](backend/app/core/telemetry.py) and initialized once in `main.py`'s lifespan. It is **off by default** and no-op-safe — `get_tracer()` returns OTel's no-op tracer when disabled, so the `@traced(...)` decorator and inline spans cost nothing and change no behavior.

- `OTEL_ENABLED=true` → traces print to the **console** (free, no backend; this is "Phase 1").
- `OTEL_EXPORTER_OTLP_ENDPOINT=<url>` → ships traces via OTLP to a backend (SigNoz/Grafana/etc.) and implies enabled. `OTEL_SERVICE_NAME` defaults to `repointel-api`.

Auto-instrumentation (FastAPI requests, `httpx`, `redis`) is wired in `_instrument_libraries`. Manual spans cover the two slow pipelines: the agent flow ([orchestrator.py](backend/app/agents/orchestrator.py) — `agent.query` → `agent.retrieve` → per-node `agent.*` spans) and indexing ([indexing_worker.py](backend/app/workers/indexing_worker.py) — `index.pipeline` → `index.fetch` / `index.embed_batch` / `index.build_graph`, with file/chunk counts as span attributes). Add new spans with `@traced("name")` for whole functions or `tracer.start_as_current_span("name")` for blocks.

## Conventions & gotchas

- Backend logging is **structlog** (`structlog.get_logger()`), not stdlib logging — pass structured kwargs, not f-strings.
- Config secrets (`QDRANT_*`, `GROQ_API_KEY`, `REDIS_URL`, `GITHUB_TOKEN`) are `.strip()`-ed by a validator in [backend/app/core/config.py](backend/app/core/config.py) because pasted keys often carry a trailing newline that breaks HTTP headers. Keep that behavior.
- CORS allows configured origins **plus** any `*.vercel.app` via regex (see `main.py`) — don't add Vercel previews to the list manually.
- `KnowledgeGraphService` keeps an in-memory `_graphs` dict but the query route constructs a fresh instance per request, so cross-request graph reads fall back to the Redis-cached serialized graph (`get_graph_data`), not the in-memory one.
- Deployment: the **root** `Dockerfile` builds the backend only, for Hugging Face Spaces, on **port 7860** (not 8000). The frontend deploys separately to Vercel with Root Directory = `frontend`. `backend/Dockerfile` is the compose/dev image.
- Python 3.12, `ruff`/`black` line-length 100; ruff ignores `E501`/`F401`. `tsconfig` is strict.
