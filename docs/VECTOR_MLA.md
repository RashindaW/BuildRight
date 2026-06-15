# Smart Handy Man 🤖 — Vector Institute MLA (Cohort 12) skills mapping

This project is a **guardrailed, multi-agent AI shopping assistant** for a hardware
store, deployed live (free) on Hugging Face Spaces. It is built to demonstrate the
**Generative AI & Agentic AI** competencies the Vector MLA cohort selects for.

**Cohort framing:** it sits squarely in **Intelligent Search & Assistants** (hybrid
RAG product/policy search, an agentic tool-use assistant) and **Personalization &
Customer Experience** (session memory, recommendations, CSAT). Anchor concepts —
**Foundation Models, Prompt Engineering, RAG, Fine-tuning** — are all exercised.

---

## 1. Core technical skills

| Requirement | Where it's demonstrated |
|---|---|
| **Python** | FastAPI backend, SQLAlchemy, the whole `backend/app/**`. |
| **A hands-on ML project (design→dev→deploy)** | This system, designed in phases, built, tested (244 tests), and **deployed live** on HF Spaces. |
| **Prompt engineering** | `app/ai/guardrails.py::SYSTEM_PROMPT_RETAIL` — layered rules (no-invention, no-price-guessing, apologize+alternative, citation, personalization); per-turn router prompt. |
| **RAG** | `app/ai/hybrid.py` — hybrid retrieval fusing **lexical + vector** arms via **Reciprocal Rank Fusion** over the product catalog, a policy KB, and ~195 product **buying-guide** docs. |
| **Embeddings + semantic search** | `app/models/product_embedding.py` + `app/ai/embeddings/` — 384-dim embeddings (`EmbeddingType` → pgvector on Postgres / JSON on SQLite); vector search in `vector_index.py`. |
| **Fine-tuning** | `app/ml/train_router.py` — fine-tunes **DistilBERT** (HF Transformers + PyTorch) to classify a turn `simple`/`complex` for the model router; `train_router_lite.py` (TF-IDF+LogReg) gives a reproducible result here (**100% acc vs 78% heuristic** on held-out synthetic data — `app/ml/report.md`). |
| **Autonomous agents + tool use** | `app/ai/service.py::stream_chat` — a multi-round tool-use loop over 11 tools (`app/ai/tools.py`): product/KB search, reorder, **project planner** (`compute_materials`/`add_materials_to_cart`), recommenders, preference memory. |
| **Memory** | `UserPreference` + `build_memory_preamble` (injected per turn) + per-conversation `summary` + a "what we remember" UI panel + `GET /chat/memory`. |
| **Synthetic data generation** | Deterministic catalog generator (10k SKUs), buying-guide docs, and **labeled** synthetic training data (`app/ml/synth_data.py`). |
| **AI-powered / automated workflows** | Agentic checkout assist, OCR stock-intake (vision → confirm → audited update), voice ordering (STT → chat), chat→cart→order attribution. |
| **PyTorch / TensorFlow** | PyTorch in `app/ml/train_router.py` (DistilBERT fine-tune). |
| **Hugging Face Transformers** | DistilBERT tokenizer/model in the fine-tune; fastembed (BGE) for embeddings. |
| **OpenAI APIs / Agent SDK (or equivalent)** | Anthropic Claude (tool-use, multi-agent router Haiku→Sonnet) + **Groq** (OpenAI-compatible) for Whisper STT. |
| **LangChain / LlamaIndex** | `app/ai/llamaindex_retriever.py` — an alternative LlamaIndex-style retriever over the same chunks, behind a flag (the primary RAG is hand-built for full control + the price guardrail). |
| **Streamlit / Gradio** | `gradio_app.py` — a Gradio "RAG & guardrail playground" exposing search + the assistant. |
| **Deploying AI (production-like)** | Single-container Docker on HF Spaces (FastAPI serves the SPA single-origin), seeds at startup, CI on push. |
| **FastAPI backend** | The entire API. |
| **MLOps / experiment tracking** | **AI Operations** dashboard (per-turn cost, route mix, tool usage, guardrail rate), offline **chat-quality eval** (faithfulness/relevance/context), CSAT, and the fine-tune `metrics.json`/`report.md`. |
| **Cloud (GCP/AWS/Azure)** | Live on HF; **`docs/CLOUD_DEPLOY.md`** documents the GCP Cloud Run / AWS ECS path (the image is cloud-agnostic — only `DATABASE_URL` + secrets change). |

## 2. Applied & professional skills

| Requirement | Where |
|---|---|
| **Business framing** | A real SME use case (hardware retail): cut "where is it / how do I choose / is it in stock" load, lift basket size via recommendations + project planning, and **measure AI-attributed revenue** + **CSAT**. |
| **MVP + iterate on feedback** | Shipped in small phases, each tested + committed + deployed; iterated directly on user feedback across the build. |
| **Technical + non-technical stakeholders** | `/about` (architecture + capabilities) and `/how-to-test` (a copy-paste tour) for non-technical reviewers; this doc + the code for technical ones. |
| **Rigorous evaluation** | Deterministic price guardrail + `validate_response`; offline RAG/answer eval; CSAT loop; classifier eval vs baseline. |
| **Data readiness / infra constraints** | Dual DB (SQLite dev / Postgres+pgvector prod) via one abstraction; graceful embedding fallback; free-tier-first design. |
| **Clean delivery / docs** | README, this mapping, `HF-DEPLOY.md`, `CLOUD_DEPLOY.md`, `DEMO.md`, inline docstrings, a green test suite. |

## 3. Honest notes (framing the gaps)

- **Fine-tuning** runs as an *offline* step (DistilBERT on a torch host; a scikit-learn
  model reproduces the result on any machine). The live router stays cheap
  (heuristic + Haiku) by design — cost-optimization is a first-class goal.
- **Cloud:** the live demo is on HF Spaces (free, instant, reviewable). Production on
  GCP/AWS is **config, not rewrite** — see `docs/CLOUD_DEPLOY.md`.
- **LangChain/LlamaIndex & Gradio** are included as alternative surfaces; the primary
  app is hand-built so the **price guardrail** and **multi-agent routing** are fully
  under control — a deliberate engineering choice worth discussing.
