# Aegis — Standalone Multi-Agent Enterprise Intelligence Platform

Aegis is a self-contained application for analysing uploaded business documents and datasets through a transparent LangGraph workflow. It does **not** depend on AtlasRAG or any external retrieval service.

## What is implemented

- **Supervisor and Planner agents** coordinate each analysis with LangGraph.
- **Knowledge Retrieval agent** searches Aegis-ingested PDF, DOCX, TXT and Markdown documents using a local BM25 index persisted in the application database. When Ollama embeddings are configured, retrieval combines BM25 with cosine-similarity reranking; lexical BM25 remains available without embeddings.
- **Data Analyst agent** analyses uploaded CSV datasets with Pandas. There is no seeded financial sample data and no user-supplied SQL or Python execution.
- **Verification agent** checks whether evidence has source metadata and whether conclusions have uploaded input. It explicitly does not claim to prove source truth.
- **Reporting agent** creates an evidence-grounded report. Ollama/OpenAI-compatible chat models are optional; transparent deterministic mode is available when no model is configured.
- React + TypeScript dashboard for analysis, file uploads, run history and evidence traces.
- SQLite local persistence; PostgreSQL supported through `DATABASE_URL`.
- API key protection, upload size/row limits, content-type/extension allowlists, CORS allowlist and security headers.

## Requirements

- Python 3.11+
- Node.js 20+
- npm
- Optional: Ollama for local chat/embedding models

## Local setup

From the repository root:

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements-dev.txt
PYTHONPATH=backend python -m uvicorn app.main:app --app-dir backend --reload
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. API docs: http://localhost:8000/docs.

## Optional local LLM (Ollama)

Install Ollama, pull a chat model and optionally an embedding model. Then set in `.env`:

```dotenv
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama3.2:3b
LLM_API_KEY=
EMBEDDING_URL=http://localhost:11434/api/embeddings
EMBEDDING_MODEL=nomic-embed-text
```

Restart the backend after editing `.env`. If chat is unavailable, the system clearly marks the run as template/fallback mode; it does not pretend an LLM was used. Document retrieval always supports BM25. When configured, embeddings participate in a weighted hybrid reranking step; otherwise retrieval is BM25-only.

## Use

1. Upload one or more PDF, DOCX, TXT or Markdown files in **Knowledge Base**.
2. Upload a CSV in **Data Workspace**. The UI lets you select a dataset for a run.
3. Submit a question. The agents retrieve matching document chunks and/or analyse the selected dataset.
4. Inspect report, evidence sources, verification status, warnings and execution trace.

CSV analysis reports numeric summaries (count, sum, mean, min, max) and top categorical values. It does not infer causality or silently invent business context. Ensure uploaded CSVs are authorised and appropriately minimised.

## Docker Compose

Set a strong `POSTGRES_PASSWORD` in `.env`, then:

```bash
docker compose up --build
```

Dashboard: http://localhost:3000; API: http://localhost:8000/docs. The Compose stack uses PostgreSQL. For production, configure `AEGIS_API_KEY`, HTTPS termination, secret management, backups, retention, monitoring, SSO/tenant isolation and security/load testing. Do not expose PostgreSQL publicly.

## API endpoints

- `GET /health`, `GET /ready`, `GET /api/v1/metrics`
- `POST /api/v1/documents` (multipart `file`), `GET /api/v1/documents`, `DELETE /api/v1/documents/{id}`
- `POST /api/v1/datasets` (multipart CSV `file`), `GET /api/v1/datasets`, `DELETE /api/v1/datasets/{id}`
- `POST /api/v1/analyze`
- `GET /api/v1/runs?limit=20`, `GET /api/v1/runs/{id}`

If `AEGIS_API_KEY` is configured, send `X-API-Key` with API requests. The dashboard has an API-key field under the analysis form.

## Tests

```bash
PYTHONPATH=backend python -m pytest backend/tests -v
```

The test suite covers API validation, no-fabricated-data behavior, run persistence, document ingestion/retrieval and CSV upload/analysis. Also run `cd frontend && npm ci && npm run build` to type-check and build the UI.

## Important limitations / production checklist

This is a deployable application foundation, not a claim of production certification. BM25 is lexical retrieval; optional embeddings are not yet used in ranking. There is no multi-tenant document ACL, SSO/OIDC, distributed rate limiting, antivirus scanning, audit export or formal regulatory compliance. Add those controls and perform threat modelling, penetration testing, load testing and operational validation before processing sensitive enterprise data. Use a managed secret store and TLS in any shared deployment.
