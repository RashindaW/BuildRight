<!-- Hugging Face Spaces metadata (Docker SDK). Harmless on GitHub. See HF-DEPLOY.md. -->
---
title: BuildRight Hardware
emoji: 🔧
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 8000
pinned: false
---

# BuildRight Hardware — Conversational Retail Store with Hybrid RAG

A professional, secure, full-stack online store for a Canadian-Tire-style hardware retailer,
built around a **guardrailed AI store assistant** with **hybrid retrieval (vector + keyword)**
over both the product catalog and a policy/FAQ knowledge base.

The assistant **never invents products, never guesses prices, apologizes for items it doesn't
carry, and cites a policy document before answering returns/warranty/shipping questions** — and the
price guardrail is proven on every push by an automated, keyless test suite.

```
React (Vite + Tailwind) SPA  ──REST + SSE──▶  FastAPI backend  ──▶  SQLite / PostgreSQL+pgvector
        │                                          │
        ├── streaming chat widget                  ├── AI core: tool-use loop + guardrails
        ├── Stripe Payment Element                 ├── Hybrid RAG (RRF: fastembed + keyword)
        └── cart / checkout / orders               ├── auth (argon2 + cookie-JWT + CSRF + RBAC)
                                                    ├── Stripe test-mode payments
                                                    └── Anthropic Claude (claude-haiku-4-5)
```

---

## What the assistant can do

- **Product search** (`search_products`) — hybrid retrieval over the catalog; grounded prices.
- **Policy / FAQ** (`search_knowledge_base`) — hybrid retrieval over `knowledge_base/*.md`
  (returns, refunds, warranty, shipping, price-match, store policies, FAQ), answered **with citations**.
- **Order memory** (logged-in) — `get_order_history` ("what did I buy last month?") and
  `reorder` ("add that drill again", bounded to the user's own purchase history).
- **Preferences** (logged-in) — `get_preferences` / `set_preference` (e.g. "I prefer Mastercraft tools"),
  injected into later turns as fenced, untrusted reference data.

## The guardrails (the heart of the product)

1. **No invented products** — only items returned by `search_products`.
2. **No guessed prices** — only prices returned verbatim; never confirms a customer's asserted price
   ("is the drill $500?"). Enforced by a **deterministic output validator** that blocks any ungrounded
   price even if the model slips; price-bearing chunks are **buffered until validated** during streaming.
3. **Apologize for items we don't carry.**
4. **Policy grounding** — policies are only stated from `search_knowledge_base` results and cited as
   *Document › Section*; out-of-KB questions defer to customer service (soft-checked).

These live in `backend/app/ai/guardrails.py` (`SYSTEM_PROMPT_RETAIL`, `validate_response`, `validate_citations`).

---

## Hybrid RAG

- **Embeddings** — local [`fastembed`](https://github.com/qdrant/fastembed) `BAAI/bge-small-en-v1.5`
  (384-dim, offline, no API key). A deterministic `hash` provider is available for download-free runs
  (`EMBEDDING_PROVIDER=hash`).
- **Fusion** — Reciprocal Rank Fusion (`backend/app/ai/hybrid.py`) blends a **keyword arm**
  (`retrieval._score_item`) with a **vector arm**, over both the catalog and the KB. RRF needs only ranks,
  so the integer lexical score and float cosine never need normalization.
- **Dual backend** — `EmbeddingType` compiles to `vector(384)` on **Postgres + pgvector** and `JSON` on
  **SQLite**; `PgVectorIndex` (`<=>` cosine) vs `NumpyVectorIndex` (in-Python cosine) is chosen by dialect.
  If the embedding backend can't load, the seed logs loudly and continues — retrieval degrades to lexical-only.

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

# Create backend\.env  (NEVER commit this — it is gitignored). See backend\.env.example:
#   ANTHROPIC_API_KEY=sk-ant-...
#   SECRET_KEY=<32+ random chars>
#   ADMIN_EMAIL / ADMIN_PASSWORD
#   STRIPE_SECRET_KEY / STRIPE_PUBLISHABLE_KEY  (test mode; optional until checkout)

python -m app.seed                 # tables + 37-product catalog + KB + embeddings + admin
uvicorn app.main:app --reload      # http://localhost:8000  (docs at /docs in dev)

# (optional) product photos -> frontend/public/img/menu/ (gitignored; seed auto-wires):
#   python ..\scripts\fetch_images.py ; python -m app.seed
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
succeeds. No webhook tunnel is required locally: after `confirmPayment` resolves, the frontend calls
`POST /payments/confirm/{order_id}`, which **re-fetches the PaymentIntent from Stripe** (source of truth)
and validates the amount + currency before marking the order paid.

- **Test card:** `4242 4242 4242 4242`, any future expiry, any CVC.
- **Failure card:** `4000 0000 0000 0002` → order stays `pending_payment`.
- **Webhook parity (optional):** `stripe listen --forward-to localhost:8000/api/v1/payments/webhook`.

---

## Testing

| Tier | Command (in `backend/`) | Needs API key? | Proves |
|---|---|---|---|
| Unit | `pytest tests/unit/` | No | RRF, chunking, embeddings, citation guard, tool executors |
| Retrieval golden (GR) | `pytest tests/golden/` | No | retrieval behaves like the PoC (frozen cafe corpus) |
| API | `pytest tests/api/` | No | auth, IDOR, cart/orders, security headers, SSE wiring |
| Migration | `alembic upgrade head` on a blank DB | No | the baseline creates the full schema |
| Retail golden (GL) | `python ..\golden_tests_retail.py` | **Yes** | end-to-end retail guardrails + price grounding |
| Frontend | `npm run test` (in `frontend/`) | No | components / format / sanitize |
| E2E | `npm run e2e` (in `frontend/`)¹ | Yes | order flow + chat guardrail + policy citation in a browser |

¹ E2E needs both servers running and a one-time `npx playwright install chromium`.

The frozen cafe corpus (`menu_data_legacy_cafe.py`) keeps the original lexical-retrieval regression
baseline green even though the live catalog is now retail.

---

## Prove the SQLite → PostgreSQL + pgvector swap

```powershell
$env:ANTHROPIC_API_KEY="sk-ant-..."; $env:SECRET_KEY="<random>"
docker compose up --build      # api talks to Postgres (pgvector/pgvector:pg16) via DATABASE_URL
# then, against Postgres:  alembic upgrade head ; python -m app.seed
```

---

## Features

- **AI assistant** — multi-turn, streaming (SSE), hybrid-RAG-grounded every turn; tool-use dispatch over
  6 tools; inbound moderation + prompt-injection heuristics (including on stored preferences);
  per-conversation token caps; anonymous or logged-in.
- **Catalog** — 37 products across 11 retail categories; product tags + handling flags, modifiers, search + filters.
- **Knowledge base** — markdown policy/FAQ docs chunked by heading and embedded for cited answers.
- **Ordering & payments** — cart, **Stripe test-mode checkout** with amount-validated settlement,
  order history, reorder-from-history.
- **Admin** — catalog CRUD, order status workflow, user list, audit log; all behind `require_admin`.
- **Security** — argon2id passwords; JWT in httpOnly+SameSite cookies; CSRF double-submit; RBAC + IDOR
  guards; rate limiting; security headers + strict CORS; integer-cents money; no stack traces to clients.

## Repo layout

```
menu_data.py                       # live retail catalog (source of truth for the seed)
menu_data_legacy_cafe.py           # frozen cafe corpus (lexical-retrieval regression baseline)
golden_tests_retail.py             # live retail guardrail gate (needs API key)
knowledge_base/*.md                # policy / FAQ documents (chunked + embedded)
backend/app/{core,models,schemas,api/routers,ai,ai/embeddings,safety,services,seed}/
backend/migrations/                # Alembic (full-schema baseline)
backend/tests/{unit,api,golden}/
frontend/src/{pages,components,lib,hooks,context,store,types}/
docker-compose.yml, backend/Dockerfile, .github/workflows/ci.yml, scripts/smoke.ps1
```

## License

MIT — see [LICENSE](./LICENSE).
