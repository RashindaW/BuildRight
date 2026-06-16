---
title: BuildRight AI
emoji: 🤖
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 8000
pinned: false
---

# BuildRight AI 🤖 - Guardrailed, Agentic RAG Commerce Assistant

<!-- The YAML block above is Hugging Face Spaces config (Docker SDK). See HF-DEPLOY.md. -->

> **🔗 Live demo:** **https://rashindaw-buildright.hf.space** &nbsp;·&nbsp; one Docker container, seeded at startup.

> **Want the deep-dive?** See **[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)** for the full engineering
> reference - architecture diagrams, data model, the AI subsystem, hybrid RAG, guardrails, and deployment.

**BuildRight AI** is a full-stack hardware-store web app fronted by a **guardrailed AI shopping
assistant**. Customers search products, get cited policy answers, plan whole projects, reorder past
purchases, and check out with Stripe - **just by chatting**. It pairs **hybrid retrieval (lexical +
vector + visual)** over the catalog and a policy knowledge base with a **deterministic guardrail** that
validates every answer against retrieved data, a **cost-aware Haiku→Sonnet model router**, and
**multimodal** (image / voice / OCR) input - all deployed as a single container.

The assistant **never invents products, never guesses prices, apologizes for items it doesn't carry, and
cites a policy document before answering returns/warranty/shipping questions** - and the price guardrail
is proven on every push by a keyless, automated test suite (~267 tests).

```
React (Vite + Tailwind) SPA  ──REST + SSE──▶  FastAPI (single origin)  ──▶  SQLite / Postgres + pgvector
        │                                          │
        ├── streaming chat widget                  ├── model router (Haiku → Sonnet)
        ├── image / voice / OCR upload             ├── agentic tool-use loop  +  two-layer guardrails
        ├── Stripe Payment Element                 ├── hybrid RAG (RRF: lexical + BGE vector + CLIP) + re-rank
        └── cart / checkout / manager dashboards   ├── auth (argon2 + cookie-JWT + CSRF + 4-tier RBAC)
                                                    ├── Stripe checkout / refunds  ·  AI-Ops observability
                                                    └── Anthropic Claude (haiku-4-5 · sonnet-4-6)
```

---

## What the assistant can do

- **Product search** - hybrid retrieval over a generated catalog (**scales to 10K+ SKUs**, 19 categories); grounded prices.
- **Policy / FAQ** - hybrid retrieval over `knowledge_base/*.md` plus generated buying/category guides, answered **with citations** (`Title › Section`).
- **Project planning (agentic)** - *"paint my 12×10 room"* triggers **clarifying questions** (dimensions), then computes a bill of materials and **adds the whole list to the cart in one step**.
- **Order memory & reorder** - *"what did I buy last month?"* / *"add that drill again"*, bounded to the user's own history.
- **Recommendations** - collaborative ("frequently bought with") + content-similar + complementary upsells.
- **Preferences (memory)** - captured during chat ("I prefer Mastercraft tools") and injected into later turns as fenced, injection-hardened reference data.
- **Multimodal** - 🖼️ photo → product search · 🎤 voice → order (Whisper STT) · ✍️ handwritten stock-sheet **OCR** (confirm-then-audit).

## The guardrails (the heart of the product)

Two independent layers (`backend/app/ai/guardrails.py`):

1. **Prompt rules** (`SYSTEM_PROMPT_RETAIL`) - only discuss tool-returned products; never invent/guess prices; apologize for missing items and offer a real in-stock alternative; cite policies as *Title › Section*.
2. **Deterministic validator** (`validate_response`) - extracts every price the model *claims*, distinguishes thresholds ("under $5") from assertions, and checks each against the **grounded** items for the turn (allowing qty × unit-price line totals). A fabricated price is **structurally blocked** and replaced with a safe fallback; `validate_citations` soft-checks policy grounding.

The safety net is **code, not a prompt** - even if the model slips, an ungrounded price never reaches the user.

## Cost-aware model routing

Each turn is classified cheaply: an image forces the heavy model; obvious project language escalates without a round-trip; very short asks stay simple; ambiguous ones get a **4-token Haiku micro-classification** (fails safe to the cheap model). Simple turns run on **Haiku**, only complex/multimodal turns pay for **Sonnet** - and the chosen route + per-turn cost is recorded for the AI-Ops dashboard.

---

## Hybrid RAG (lexical + vector + visual)

Three independent retrieval arms fused with **Reciprocal Rank Fusion** (`k=60`):

- **Lexical** - keyword scoring with field weighting + singularization + an exact-SKU fast path (`backend/app/ai/retrieval.py`).
- **Dense vector** - [`fastembed`](https://github.com/qdrant/fastembed) `BAAI/bge-small-en-v1.5` (384-d, offline, no API key); a deterministic `hash` provider exists for download-free runs (`EMBEDDING_PROVIDER=hash`).
- **Visual (CLIP)** - optional 512-d image embeddings let a text query rank products by appearance; torch-guarded, so it's a no-op (and the fuser is unchanged) where torch is absent.

After fusion, a **cross-encoder re-ranker** sharpens precision (with a deterministic feature re-ranker fallback), and a **query-decomposition** step handles "X vs Y" comparisons via multi-hop retrieval.

**Measured, not guessed.** An evaluation harness (`backend/app/ai/eval/`) scores `hit@k` / `MRR` / `nDCG@k`
over labeled question→doc sets - the re-ranker's lift (KB **hit@5 0.86 → 0.93**) is a measurement, not a claim.

**Dual backend** - `EmbeddingType` compiles to `vector(384)` on **Postgres + pgvector** (HNSW-indexed) and
`JSON` on **SQLite**; `PgVectorIndex` (`<=>` cosine) vs `NumpyVectorIndex` (in-Python cosine) is chosen by
dialect. If the embedding backend can't load, the seed logs loudly and retrieval degrades to lexical-only.

---

## Quick start (Windows PowerShell)

### Prerequisites
Python 3.10+, Node 18+, Git. (Docker optional, for the Postgres + pgvector swap.)

### 1. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt

# Create backend\.env  (NEVER commit this - it is gitignored). See backend\.env.example:
#   ANTHROPIC_API_KEY=sk-ant-...
#   SECRET_KEY=<32+ random chars>
#   ADMIN_EMAIL / ADMIN_PASSWORD
#   STRIPE_SECRET_KEY / STRIPE_PUBLISHABLE_KEY  (test mode; optional until checkout)
#   CATALOG_TARGET=3000     (omit for the curated ~1.2k catalog; e.g. 10000 for the big one)

python -m app.seed                 # tables + generated catalog + KB + embeddings + admin
uvicorn app.main:app --reload      # http://localhost:8000  (docs at /docs in dev)
```

### 2. Frontend

```powershell
cd frontend
npm install
npm run dev                        # http://localhost:5173  (proxies /api to :8000)
```

Open http://localhost:5173, sign up, browse products, chat with the assistant, and check out.

> **Security note:** the Anthropic and Stripe **secret** keys are read server-side only and never shipped
> to the browser (only the Stripe *publishable* key reaches the client). `.env` files are gitignored.

---

## Stripe test-mode checkout

Checkout uses the Stripe **Payment Element**. The order flows `pending_payment → placed` once payment
succeeds. No webhook tunnel is required: after `confirmPayment` resolves, the frontend calls
`POST /payments/confirm/{order_id}`, which **re-fetches the PaymentIntent from Stripe** (source of truth)
and validates amount + currency before marking the order paid. Refunds are manager-gated and audited.

- **Test card:** `4242 4242 4242 4242`, any future expiry, any CVC.
- **Failure card:** `4000 0000 0000 0002` → order stays `pending_payment`.
- **Webhook parity (optional):** `stripe listen --forward-to localhost:8000/api/v1/payments/webhook`.

---

## Testing

| Tier | Command (in `backend/`) | Needs API key? | Proves |
|---|---|---|---|
| Unit | `pytest tests/unit/` | No | RRF, chunking, embeddings, re-rank, query-expand, guardrail/pricing, router, eval metrics, vision/CLIP |
| Retrieval golden | `pytest tests/golden/` | No | retrieval quality + validator regression on a frozen corpus |
| API | `pytest tests/api/` | No | auth, RBAC/IDOR, cart/orders, guest checkout, refunds, analytics, CSAT, SSE wiring |
| Migration | `alembic upgrade head` on a blank DB | No | the additive Alembic chain creates the full schema |
| Frontend | `npm run test` (in `frontend/`) | No | components / format / sanitize |

The full suite (~267 tests) is **keyless and deterministic**; CI runs it against **both SQLite and a real
Postgres + pgvector** service to prove the database abstraction holds.

---

## Prove the SQLite → PostgreSQL + pgvector swap

```powershell
$env:ANTHROPIC_API_KEY="sk-ant-..."; $env:SECRET_KEY="<random>"
docker compose up --build      # api talks to Postgres (pgvector/pgvector:pg16) via DATABASE_URL
# then, against Postgres:  alembic upgrade head ; python -m app.seed
```

---

## Feature summary

- **AI assistant** - multi-turn streaming (SSE), hybrid-RAG-grounded every turn, an agentic tool-use loop (product/KB search, project planner, reorder, recommenders, preferences), inbound moderation + prompt-injection heuristics, per-conversation token caps; anonymous or logged-in.
- **Catalog** - a deterministic generator (categories × product types × variant axes × brands) scaling to **10K+ SKUs** across **19 categories**, with branded SVG placeholder imagery (no image files shipped).
- **Knowledge base** - markdown policy/FAQ docs + ~195 buying guides + 19 category guides, heading-chunked and embedded for cited answers; optional PDF / spec-sheet / OCR ingestion.
- **Ordering & payments** - guest-capable cart, **Stripe test-mode checkout** with amount-validated settlement, manager refunds, order history, reorder-from-history.
- **Observability** - per-turn cost / route mix / guardrail-violation telemetry, AI-attributed revenue, offline answer-quality eval, CSAT, inventory & margins - behind a manager dashboard.
- **Security** - argon2 passwords; JWT (refresh-rotation) in httpOnly+SameSite cookies; CSRF double-submit; **4-tier RBAC** + IDOR guards; rate limiting + login lockout; audit log; integer-cents money; no stack traces to clients.

## Repo layout

```
menu_data.py                       # curated retail catalog (source for the curated seed)
knowledge_base/*.md                # policy / FAQ documents (chunked + embedded)
docs/                              # ARCHITECTURE.md · CLOUD_DEPLOY.md
backend/app/{core,models,schemas,api/routers,services,seed}/
backend/app/ai/{,embeddings,eval}  # router, tools, hybrid, rerank, query_expand, guardrails, vision, voice
backend/app/mcp/                   # stdio MCP server exposing read-only catalog tools
backend/migrations/                # Alembic (additive, dialect-aware: SQLite + pgvector)
backend/tests/{unit,api,golden}/   # ~267 keyless tests
frontend/src/{pages,components,lib,hooks,context,store,types}/
Dockerfile, docker-compose.yml, .github/workflows/{ci.yml,deploy-hf.yml}
```

## Documentation

| Doc | What it covers |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Full engineering reference - architecture diagrams, data model, AI subsystem, RAG, guardrails, deployment. |
| [`HF-DEPLOY.md`](HF-DEPLOY.md) · [`docs/CLOUD_DEPLOY.md`](docs/CLOUD_DEPLOY.md) | Deploy SOP (Hugging Face Spaces) + cloud migration path. |

## License

MIT - see [LICENSE](./LICENSE).
