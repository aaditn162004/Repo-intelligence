# RepoIntel — AI-Powered Repository Intelligence Platform

> Deep codebase understanding through semantic retrieval, AST parsing, dependency graphs, and multi-agent AI reasoning.

[![CI](https://github.com/your-org/repo-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/repo-intelligence/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=next.js)](https://nextjs.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What It Is

RepoIntel is a **production-grade AI engineering platform** that lets developers deeply understand any codebase using natural language. It goes far beyond a RAG chatbot — it combines:

- **AST-level code parsing** (Tree-sitter, 10+ languages)
- **Semantic vector search** (BAAI/bge embeddings in Qdrant)
- **Dependency graph analysis** (NetworkX + React Flow)
- **Multi-agent LLM reasoning** (LangGraph + Qwen2.5-Coder via Ollama)
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
| LLM | Qwen2.5-Coder:7b via Ollama |
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
| CI/CD | GitHub Actions |

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- 16 GB RAM (for Qwen2.5-Coder:7b)
- NVIDIA GPU (optional, for faster inference)

### 1. Clone and start

```bash
git clone https://github.com/your-org/repo-intelligence.git
cd repo-intelligence

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
│   │   ├── core/            # Config, logging
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
├── .github/workflows/       # CI + Deploy pipelines
└── docker-compose.yml
```

---

## Configuration

All backend settings via environment variables (see `backend/.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_MODEL` | `qwen2.5-coder:7b` | Ollama model name |
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | HuggingFace model |
| `QDRANT_HOST` | `localhost` | Qdrant hostname |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API |
| `MAX_REPO_SIZE_MB` | `500` | Max repository size |
| `TOP_K_RESULTS` | `10` | Retrieval top-k |
| `GITHUB_TOKEN` | `` | For private repos |

---

## Deployment

### Render (Backend)

1. Create a new **Web Service** pointing to the `backend/` directory
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables (Qdrant Cloud, Upstash Redis, Ollama Cloud)
5. Add `RENDER_DEPLOY_HOOK_URL` secret to GitHub for auto-deploy

### Vercel (Frontend)

```bash
cd frontend
npx vercel --prod
# Set NEXT_PUBLIC_API_URL to your Render backend URL
```

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
