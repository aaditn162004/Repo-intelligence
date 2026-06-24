---
title: RepoIntel API
emoji: 🔍
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
short_description: "AI repo intelligence: semantic code search + AI agents"
---

# RepoIntel — AI-Powered Repository Intelligence Platform

> Deep codebase understanding through semantic retrieval, AST parsing, dependency graphs, and multi-agent AI reasoning.

[![CI](https://github.com/aaditn162004/Repo-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/aaditn162004/Repo-intelligence/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=next.js)](https://nextjs.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🚀 Live Demo

| Service | URL |
|---------|-----|
| **Frontend (try it here)** | **[repo-intelligence-two.vercel.app](https://repo-intelligence-two.vercel.app)** |
| **Backend API** | [aaditn-repointel-api.hf.space](https://aaditn-repointel-api.hf.space) |
| **API Docs (Swagger)** | [aaditn-repointel-api.hf.space/api/docs](https://aaditn-repointel-api.hf.space/api/docs) |

> ⏳ The backend runs on Hugging Face's free tier and **sleeps after inactivity** — the first request may take 30–60s to wake the Space.

---

## What It Is

RepoIntel is a **production-grade AI engineering platform** that lets developers deeply understand any codebase using natural language. It goes far beyond a RAG chatbot — it combines:

- **AST-level code parsing** (Tree-sitter, 10+ languages)
- **Semantic vector search** (BAAI/bge embeddings in Qdrant)
- **Dependency graph analysis** (NetworkX + React Flow)
- **Multi-agent LLM reasoning** (LangGraph — Groq in the cloud, or Qwen2.5-Coder via Ollama locally)
- **Streaming AI responses** (SSE)

Ask questions like:
- *"Explain the authentication flow"*
- *"Where is JWT validation implemented?"*
- *"What services break if I change this API?"*
- *"Trace the request lifecycle for login"*
- *"Generate documentation for UserService"*
- *"Find potential bugs in session management"*

---

## Architecture

```
GitHub Repository / ZIP Upload
         │
         ▼
┌─────────────────────┐
│  Repository Cloner  │  (GitPython, async background task)
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  AST Parser Engine  │  (Tree-sitter — Python, JS, TS, Java, Go, Rust…)
│  Language Detector  │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Structure-Aware    │  (Chunk by AST node type, not naive text windows)
│  Code Chunker       │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Embedding Pipeline │  (BAAI/bge-small-en-v1.5, batched, async)
│  → Qdrant Storage   │  (Per-repository collection, cosine similarity)
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Knowledge Graph    │  (NetworkX DiGraph: files, functions, classes)
│  Dependency Builder │  (imports, calls, inherits, contains edges)
└────────┬────────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│          LangGraph Multi-Agent Pipeline  │
│                                          │
│  ┌──────────┐    ┌──────────────────┐   │
│  │  Planner │───▶│   Retriever      │   │
│  │  Agent   │    │   (hybrid search)│   │
│  └──────────┘    └────────┬─────────┘   │
│                           │             │
│          ┌────────────────┼──────────┐  │
│          ▼                ▼          ▼  │
│  ┌──────────────┐ ┌──────────┐ ┌──────────────┐ │
│  │  Architect   │ │Documenter│ │Impact Analyser│ │
│  │  Agent       │ │  Agent   │ │    Agent      │ │
│  └──────────────┘ └──────────┘ └──────────────┘ │
│          │                │          │          │
│          └────────────────▼──────────┘          │
│                   ┌─────────────┐               │
│                   │ Synthesiser │               │
│                   │   Agent     │               │
│                   └──────┬──────┘               │
└──────────────────────────┼──────────────────────┘
                           │
                           ▼
               Streaming SSE Response → Frontend
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI + Uvicorn (async) |
| LLM | Groq (cloud) · Qwen2.5-Coder:7b via Ollama (local) |
| Embeddings | BAAI/bge-small-en-v1.5 (sentence-transformers) |
| Vector DB | Qdrant |
| Cache | Redis |
| AST Parsing | Tree-sitter + tree-sitter-languages |
| Graph Analysis | NetworkX |
| Agent Orchestration | LangGraph |
| Frontend | Next.js 15 + React 19 |
| Graph Visualisation | React Flow |
| Styling | Tailwind CSS |
| Containerisation | Docker + Docker Compose |
| Observability | OpenTelemetry (console / OTLP exporter) |
| Evaluation | Hand-rolled LLM-as-judge (Groq) |
| CI/CD | GitHub Actions |

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- 16 GB RAM (for Qwen2.5-Coder:7b)
- NVIDIA GPU (optional, for faster inference)

### 1. Clone and start

```bash
git clone https://github.com/aaditn162004/Repo-intelligence.git
cd Repo-intelligence

# Start all services (pulls Qwen model on first run ~4 GB)
docker compose up -d

# Watch logs
docker compose logs -f backend
```

### 2. Open the UI

Navigate to **http://localhost:3000**

### 3. Index a repository

1. Click **Add Repository**
2. Paste a GitHub URL (e.g. `https://github.com/tiangolo/fastapi`)
3. Wait for indexing (~2-5 min depending on repo size)
4. Click **Ask Questions** and start querying!

---

## Development Setup

### Backend (Python)

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env

# Start infrastructure only
docker compose up qdrant redis ollama -d

# Pull the LLM model
docker exec repo_intel_ollama ollama pull qwen2.5-coder:7b

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

### Run Tests

```bash
# Backend
cd backend
pytest tests/ -v

# Frontend type check
cd frontend
npm run type-check
```

### Evals

A hand-rolled evaluation harness lives in `evals/`. It runs question/answer test
cases (stored as JSON) against the deployed API and scores each answer with an
**LLM-as-judge** (Groq, LLaMA 3.1 8B), producing a Markdown report with overall
pass rate and a per-category breakdown — `factual`, `structural`, `multi_hop`.
No LangSmith / Braintrust; just `httpx` + the Groq REST API.

```bash
cd evals
pip install -r requirements.txt
export GROQ_API_KEY=gsk_...        # only key needed — the judge runs on Groq
python run_evals.py                # or: --category multi_hop, --limit 3
```

See [`evals/README.md`](evals/README.md) for the test-case format and scoring details.

---

## API Reference

Full OpenAPI docs available at **http://localhost:8000/api/docs**

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/repositories` | Ingest GitHub repository |
| `POST` | `/api/v1/repositories/upload` | Upload ZIP archive |
| `GET` | `/api/v1/repositories` | List all repositories |
| `GET` | `/api/v1/repositories/{id}/progress` | Real-time indexing progress |
| `POST` | `/api/v1/query/stream` | **Streaming** NL query (SSE) |
| `POST` | `/api/v1/query` | Non-streaming NL query |
| `GET` | `/api/v1/graph/{id}/full` | Full dependency graph |
| `GET` | `/api/v1/graph/{id}/subgraph` | File-centred subgraph |
| `GET` | `/api/v1/graph/{id}/affected` | Impact analysis |
| `POST` | `/api/v1/documentation/generate` | Generate module/API docs |
| `GET` | `/api/v1/documentation/{id}/readme` | Generate README |

---

## Project Structure

```
repo-intelligence/
├── backend/
│   ├── app/
│   │   ├── agents/          # LangGraph multi-agent pipeline
│   │   ├── api/routes/      # FastAPI route handlers
│   │   ├── core/            # Config, logging, OpenTelemetry tracing
│   │   ├── embeddings/      # Sentence-transformer wrapper
│   │   ├── graph/           # NetworkX dependency/knowledge graph
│   │   ├── models/          # Pydantic schemas
│   │   ├── parsers/         # Tree-sitter AST parser + chunker
│   │   ├── retrieval/       # Hybrid retriever + context builder
│   │   ├── services/        # Qdrant, Redis, cache services
│   │   ├── utils/           # Git, file, ZIP utilities
│   │   └── workers/         # Background indexing worker
│   └── tests/
├── frontend/
│   └── src/
│       ├── app/             # Next.js App Router pages
│       ├── components/      # Repository, Graph, Query UI
│       ├── hooks/           # SWR hooks + streaming hook
│       ├── lib/             # API client + utilities
│       └── types/           # TypeScript definitions
├── evals/                   # Eval harness — JSON cases + LLM-as-judge (Groq)
├── .github/workflows/       # CI pipeline (lint + build)
└── docker-compose.yml
```

---

## Configuration

All backend settings via environment variables (see `backend/.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `ollama` | `ollama` for local, `groq` for cloud |
| `LLM_MODEL` | `qwen2.5-coder:7b` | Ollama model name (local) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API (local) |
| `GROQ_API_KEY` | `` | Groq API key (cloud) |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model name (cloud) |
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | HuggingFace model |
| `QDRANT_HOST` | `localhost` | Qdrant hostname (local) |
| `QDRANT_URL` | `` | Qdrant Cloud URL (cloud) |
| `QDRANT_API_KEY` | `` | Qdrant Cloud API key (cloud) |
| `REDIS_URL` | `redis://localhost:6379` | Redis / Upstash connection |
| `MAX_REPO_SIZE_MB` | `500` | Max repository size |
| `TOP_K_RESULTS` | `10` | Retrieval top-k |
| `GITHUB_TOKEN` | `` | For private repos |
| `OTEL_ENABLED` | `false` | Set `true` to emit traces to the console (Phase 1) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `` | Ship traces to an OTLP backend (SigNoz, Grafana…); implies enabled |
| `OTEL_SERVICE_NAME` | `repointel-api` | Service name attached to traces |

---

## Observability

The backend is instrumented with **OpenTelemetry**. Tracing is **off by default**
(no overhead) and is enabled per-environment:

- `OTEL_ENABLED=true` → traces print to the **console** — free, no external backend
- `OTEL_EXPORTER_OTLP_ENDPOINT=<url>` → traces are shipped to any OTLP-compatible
  backend (SigNoz, Grafana Cloud, Datadog…) with **no code change**

FastAPI requests, `httpx`, and Redis are auto-instrumented. Custom spans cover the
two slow paths so you can see exactly where latency goes per request:

- **Query:** `agent.query → agent.retrieve → agent.<node>` (planner, synthesiser, …)
- **Indexing:** `index.pipeline → index.fetch / index.embed_batch / index.build_graph`

---

## Deployment

### Hugging Face Spaces (Backend)

1. Go to [huggingface.co/new-space](https://huggingface.co/new-space), choose **Docker**, name it `repointel-api`
2. Add the Space as a git remote: `git remote add space https://huggingface.co/spaces/<your-hf-username>/repointel-api`
3. Push: `git push space main`
4. In the Space's **Settings → Repository secrets**, add:
   - `LLM_PROVIDER=groq`
   - `GROQ_API_KEY=gsk_...`
   - `QDRANT_URL=https://...`
   - `QDRANT_API_KEY=...`
   - `REDIS_URL=rediss://...`
   - `CORS_ORIGINS=["https://your-app.vercel.app"]`

The API will be live at `https://<your-hf-username>-repointel-api.hf.space`

### Vercel (Frontend)

Import the repo at [vercel.com/new](https://vercel.com/new), then in **project settings**:

1. **Root Directory** → set to `frontend` (the Next.js app is not at the repo root)
2. **Environment Variables** → add `NEXT_PUBLIC_API_URL` = your HF Space URL (e.g. `https://<your-hf-username>-repointel-api.hf.space`)
   - This is baked in at **build time**, so redeploy after changing it.
3. Deploy — Vercel auto-builds on every push to `main`.

> The backend's CORS already allows any `*.vercel.app` subdomain via regex, so no extra CORS config is needed for Vercel-hosted frontends.

---

## What Makes This Different

| Feature | Generic RAG | RepoIntel |
|---------|------------|-----------|
| Code understanding | Naive text chunks | AST-level function/class extraction |
| Search | BM25 or basic cosine | Hybrid semantic + graph-expanded |
| Context | Static passages | Repository-topology-aware |
| Reasoning | Single LLM call | Multi-agent: Planner → Retriever → Specialist → Synthesiser |
| Visualisation | None | Interactive React Flow dependency graphs |
| Impact analysis | None | Graph traversal: affected files, transitive deps |

---

## License

MIT © 2024
