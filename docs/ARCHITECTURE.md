# Aegis architecture

Request → FastAPI → LangGraph Supervisor → Planner → local BM25 document retrieval and/or Pandas CSV analysis → Verification → Reporting → persisted run.

Documents and chunks are stored in SQL tables. Uploaded CSV rows are stored as structured JSON records and loaded into Pandas for deterministic descriptive analysis. LLM calls use an OpenAI-compatible chat-completions endpoint (Ollama by default); model output is treated as untrusted and is never executed as code or SQL. The system can operate in template mode without a model.
