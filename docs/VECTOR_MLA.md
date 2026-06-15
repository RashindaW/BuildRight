# BuildRight AI 🤖 — Vector Institute MLA (Cohort 12) skills mapping

This project is a **guardrailed, multi-agent AI shopping assistant** for a hardware
store, deployed live (free) on Hugging Face Spaces. It is built to demonstrate the
**Generative AI & Agentic AI** competencies the Vector MLA cohort selects for.

**Cohort framing:** it sits squarely in **Intelligent Search & Assistants** (hybrid
RAG product/policy search, an agentic tool-use assistant) and **Personalization &
Customer Experience** (session memory, recommendations, CSAT). Anchor concepts —
**Foundation Models, Prompt Engineering, RAG, and agentic tool use** — are all exercised.

---

## 1. Core technical skills

| Requirement | Where it's demonstrated |
|---|---|
| **Python** | FastAPI backend, SQLAlchemy, the whole `backend/app/**`. |
| **A hands-on ML project (design→dev→deploy)** | This system, designed in phases, built, tested (~267 tests), and **deployed live** on HF Spaces. |
| **Prompt engineering** | `app/ai/guardrails.py::SYSTEM_PROMPT_RETAIL` — layered rules (no-invention, no-price-guessing, apologize+alternative, citation, personalization); per-turn router prompt. |
| **RAG** | `app/ai/hybrid.py` — hybrid retrieval fusing **lexical + vector** arms via **Reciprocal Rank Fusion** over the product catalog, a policy KB, and ~195 product **buying-guide** docs. |
| **Embeddings + semantic search** | `app/models/product_embedding.py` + `app/ai/embeddings/` — 384-dim embeddings (`EmbeddingType` → pgvector on Postgres / JSON on SQLite); vector search in `vector_index.py`; optional **CLIP visual arm** (`clip.py`). |
| **Re-ranking** | `app/ai/rerank.py` — a sentence-transformers **cross-encoder** re-ranks the fused candidate pool (deterministic feature re-ranker as the CPU fallback); lift measured by the eval harness (hit@5 0.86→0.93). |
| **Autonomous agents + tool use** | `app/ai/service.py::stream_chat` — a multi-round tool-use loop over 11 tools (`app/ai/tools.py`): product/KB search, reorder, **project planner** (`compute_materials`/`add_materials_to_cart`), recommenders, preference memory. |
| **Memory** | `UserPreference` + `build_memory_preamble` (injected per turn) + per-conversation `summary` + a "what we remember" UI panel + `GET /chat/memory`. |
| **Synthetic data generation** | Deterministic catalog generator (10k SKUs) + generated buying-guide / category-guide knowledge docs (`app/seed/`), and a labeled retrieval-eval set (`app/ai/eval/`). |
| **AI-powered / automated workflows** | Agentic checkout assist, OCR stock-intake (vision → confirm → audited update), voice ordering (STT → chat), chat→cart→order attribution. |
| **PyTorch** | Powers the optional **CLIP visual-search arm** (`app/ai/embeddings/clip.py`) and the **cross-encoder re-ranker** (`app/ai/rerank.py`); both degrade gracefully to deterministic fallbacks where torch is absent (keeping the deployed image lean). |
| **Hugging Face / Transformers ecosystem** | sentence-transformers cross-encoder (`rerank.py`), open-clip (`clip.py`), and fastembed (BGE-small) for text embeddings. |
| **OpenAI APIs / Agent SDK (or equivalent)** | Anthropic Claude (tool-use, multi-agent router Haiku→Sonnet) + **Groq** (OpenAI-compatible) for Whisper STT. |
| **LangChain / LlamaIndex** | `app/ai/llamaindex_retriever.py` — an alternative LlamaIndex-style retriever over the same chunks, behind a flag (the primary RAG is hand-built for full control + the price guardrail). |
| **Streamlit / Gradio** | `gradio_app.py` — a Gradio "RAG & guardrail playground" exposing search + the assistant. |
| **Deploying AI (production-like)** | Single-container Docker on HF Spaces (FastAPI serves the SPA single-origin), seeds at startup, CI on push. |
| **FastAPI backend** | The entire API. |
| **MLOps / experiment tracking** | **AI Operations** dashboard (per-turn cost, route mix, tool usage, guardrail rate), the **retrieval eval harness** (`app/ai/eval/` — hit@k/MRR/nDCG → `retrieval_metrics.json`), offline **chat-quality eval** (faithfulness/relevance/context), and CSAT. |
| **Cloud (GCP/AWS/Azure)** | Live on HF; **`docs/CLOUD_DEPLOY.md`** documents the GCP Cloud Run / AWS ECS path (the image is cloud-agnostic — only `DATABASE_URL` + secrets change). |

## 2. Applied & professional skills

| Requirement | Where |
|---|---|
| **Business framing** | A real SME use case (hardware retail): cut "where is it / how do I choose / is it in stock" load, lift basket size via recommendations + project planning, and **measure AI-attributed revenue** + **CSAT**. |
| **MVP + iterate on feedback** | Shipped in small phases, each tested + committed + deployed; iterated directly on user feedback across the build. |
| **Technical + non-technical stakeholders** | `/about` (architecture + capabilities) and `/how-to-test` (a copy-paste tour) for non-technical reviewers; this doc + the code for technical ones. |
| **Rigorous evaluation** | Deterministic price guardrail + `validate_response`; the retrieval eval harness (hit@k/MRR/nDCG, measuring re-ranker lift); offline RAG/answer eval; CSAT loop. |
| **Data readiness / infra constraints** | Dual DB (SQLite dev / Postgres+pgvector prod) via one abstraction; graceful embedding fallback; free-tier-first design. |
| **Clean delivery / docs** | README, this mapping, `HF-DEPLOY.md`, `CLOUD_DEPLOY.md`, `DEMO.md`, inline docstrings, a green test suite. |

## 3. Honest notes (framing the gaps)

- **Model routing stays cheap by design:** a heuristic fast-path + a 4-token Haiku
  micro-classification decide Haiku-vs-Sonnet per turn — no extra model to train or
  serve. Transformer **fine-tuning** is intentionally scoped to a *separate, dedicated
  project* (proper labeled dataset + held-out evaluation + model card) rather than
  bolted onto this app, where the routing task is too easy to justify it.
- **Cloud:** the live demo is on HF Spaces (free, instant, reviewable). Production on
  GCP/AWS is **config, not rewrite** — see `docs/CLOUD_DEPLOY.md`.
- **LangChain/LlamaIndex & Gradio** are included as alternative surfaces; the primary
  app is hand-built so the **price guardrail** and **multi-agent routing** are fully
  under control — a deliberate engineering choice worth discussing.
