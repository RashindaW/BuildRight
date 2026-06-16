# BuildRight AI — System Architecture & Complete Documentation

> **BuildRight AI** is a full-stack hardware-store web application with a guardrailed,
> multi-agent AI shopping assistant. A single FastAPI process serves a React SPA and a
> JSON/SSE API; an Anthropic-Claude assistant answers product, policy, and project
> questions grounded in a hybrid (lexical + vector + visual) retrieval system, with
> deterministic guardrails, per-user memory, Stripe checkout, RBAC, and full cost/route
> observability. It deploys for free on Hugging Face Spaces as one Docker container and
> runs identically on Postgres + pgvector in the cloud.

**Audience:** engineers who want a single source of truth for how the system is built. For
deployment SOPs see [`../HF-DEPLOY.md`](../HF-DEPLOY.md) and [`CLOUD_DEPLOY.md`](CLOUD_DEPLOY.md).

---

## Table of contents

1. [What it is & design goals](#1-what-it-is--design-goals)
2. [Technology stack](#2-technology-stack)
3. [High-level architecture](#3-high-level-architecture)
4. [Repository layout](#4-repository-layout)
5. [Data model](#5-data-model)
6. [Backend core: auth, security, RBAC](#6-backend-core-auth-security-rbac)
7. [HTTP API reference](#7-http-api-reference)
8. [The AI assistant subsystem](#8-the-ai-assistant-subsystem)
9. [Hybrid retrieval (RAG)](#9-hybrid-retrieval-rag)
10. [Guardrails](#10-guardrails)
11. [Catalog, knowledge base & images](#11-catalog-knowledge-base--images)
12. [Payments (Stripe)](#12-payments-stripe)
13. [Observability & analytics](#13-observability--analytics)
14. [Retrieval evaluation](#14-retrieval-evaluation)
15. [Frontend architecture](#15-frontend-architecture)
16. [Configuration reference](#16-configuration-reference)
17. [Database migrations](#17-database-migrations)
18. [Testing & CI](#18-testing--ci)
19. [Deployment](#19-deployment)
20. [Local development](#20-local-development)
21. [Key design decisions](#21-key-design-decisions)

---

## 1. What it is & design goals

BuildRight AI is a realistic e-commerce storefront for a hardware retailer ("BuildRight"),
fronted by a conversational AI assistant. A shopper can browse ~1.2k–10k generated SKUs,
filter and search, add to a cart, and check out with Stripe — or simply chat: *"I'm painting
a 12×10 room, what do I need?"*, *"impact driver vs hammer drill?"*, *"what's your return
policy?"*, or upload a photo of a tool to find it.

Design goals that shaped every subsystem:

| Goal | How it's met |
| --- | --- |
| **Grounded, never hallucinated** | Two-layer guardrails: prompt rules **+** a deterministic price/citation validator that runs on every assistant turn. |
| **Cheap & fast by default** | A Haiku→Sonnet model router spends the small model on simple turns and only escalates when needed. |
| **High retrieval quality** | Hybrid lexical + vector + (optional) CLIP visual retrieval fused with Reciprocal Rank Fusion, an optional re-ranker, query decomposition, and an offline eval harness. |
| **Runs anywhere, free** | One Docker image; SQLite + in-memory vectors locally, Postgres + pgvector in the cloud — switched by one env var. Heavy/optional deps (torch, CLIP, PDF, training) live outside the deployed image. |
| **Production-shaped** | RBAC, CSRF, JWT refresh rotation, rate limiting, login lockout, audit log, Alembic migrations, CI with a real-Postgres job, observability telemetry on every turn. |

---

## 2. Technology stack

**Backend**
- Python 3.11, **FastAPI** + Starlette, **Uvicorn**
- **SQLAlchemy 2.0** ORM, **Alembic** migrations
- **SQLite** (dev/demo) or **PostgreSQL + pgvector** (prod) — same code path
- **Anthropic** SDK (Claude Haiku 4.5 / Sonnet 4.6)
- **fastembed** (BAAI/bge-small-en-v1.5, 384-dim) with a deterministic hash-embedding fallback
- **Stripe** (test mode), **slowapi** (rate limit), **passlib[argon2]** + **PyJWT** (auth), **numpy**

**Frontend**
- **React 18** + **TypeScript 5.5**, **Vite 5**, **React Router 6**
- **Tailwind CSS 3**, **Zustand** (UI state), **TanStack React Query 5** (server state)
- **Stripe.js / @stripe/react-stripe-js**, **react-markdown** + **DOMPurify**
- **Vitest** + Testing Library, **Playwright** (e2e)

**Optional / out-of-image** (never in `backend/requirements.txt`)
- `torch` + `open-clip-torch` + `Pillow` → CLIP visual arm
- `sentence-transformers` (+ `torch`) → cross-encoder re-ranker
- `pypdf` + `reportlab` → PDF / spec-sheet ingestion

**Infra:** Docker (multi-stage), Hugging Face Spaces (free), `docker-compose` (Postgres + Redis + MinIO), GitHub Actions CI/CD.

---

## 3. High-level architecture

A single FastAPI process serves both the built React SPA (static files) and the `/api/v1`
API from one origin — so there are no CORS or cross-site-cookie problems in production, and
the whole app is one deployable unit.

```
                              ┌─────────────────────────────────────────────┐
                              │            Browser (React SPA)               │
                              │  storefront · cart · chat widget · dashboards│
                              └───────────────┬─────────────────────────────┘
                                              │  HTTPS (cookies: access/refresh/csrf)
                                              │  JSON + Server-Sent Events
                              ┌───────────────▼─────────────────────────────┐
                              │         FastAPI app (single origin)          │
                              │                                              │
   static SPA  ◀─────────────│  _mount_spa()  ── serves /assets, index.html │
                              │                                              │
                              │  /api/v1 routers:                            │
                              │   auth · menu · cart · orders · chat ·       │
                              │   admin · analytics · payments · media       │
                              │                                              │
                              │  middleware: CSRF · rate limit · request-id ·│
                              │              exception handlers              │
                              └───┬───────────────┬──────────────┬──────────┘
                                  │               │              │
                  ┌───────────────▼──┐   ┌────────▼───────┐  ┌───▼──────────────┐
                  │  Services layer  │   │  AI subsystem  │  │  External APIs   │
                  │ cart/order/      │   │  service.py    │  │  Anthropic Claude│
                  │ payment/memory/  │   │  router·tools· │  │  Stripe          │
                  │ recommender/     │   │  hybrid·guard· │  │  (opt) STT/images│
                  │ analytics/audit/ │   │  embeddings    │  └──────────────────┘
                  │ eval             │   └────────┬───────┘
                  └───────┬──────────┘            │
                          │                       │
                  ┌───────▼───────────────────────▼──────────────────────────┐
                  │   SQLAlchemy ORM  ──►  SQLite (dev)  |  Postgres+pgvector  │
                  │   tables: users, menu_items, carts, orders, conversations,│
                  │   messages, documents, document_chunks, *_embeddings,     │
                  │   user_preferences, conversation_feedback, audit_logs     │
                  └───────────────────────────────────────────────────────────┘
```

**Seed-at-startup.** On container start the app runs `python -m app.seed` (idempotent): it
creates tables, generates the catalog, ingests the knowledge base + buying/category guides,
and computes embeddings. This means a fresh Space (with ephemeral storage) always boots with
a complete, searchable dataset and runtime secrets are honored.

---

## 4. Repository layout

```
Cut_Dry/
├── Dockerfile                  # multi-stage: build SPA (node) → run FastAPI (python)
├── docker-compose.yml          # postgres(pgvector) + redis + minio + api
├── menu_data.py                # curated seed catalog (~37 hand-written items)
├── README.md  HF-DEPLOY.md  DEMO.md
├── docs/
│   ├── ARCHITECTURE.md         # ← this file
│   ├── CLOUD_DEPLOY.md
├── .github/workflows/
│   ├── ci.yml                  # secret-scan, backend, backend-postgres, frontend
│   └── deploy-hf.yml           # mirror to Hugging Face Space on push
├── backend/
│   ├── app/
│   │   ├── main.py             # app factory, router mounting, SPA mount, health
│   │   ├── core/               # config, db, deps (auth), security, errors, rate_limit, lockout
│   │   ├── models/             # SQLAlchemy models (one module per aggregate)
│   │   ├── schemas/            # Pydantic request/response models
│   │   ├── api/routers/        # auth, menu, cart, orders, chat, admin, analytics, payments, media
│   │   ├── services/           # cart, order, payment, memory, recommender, analytics, audit, eval
│   │   ├── ai/                 # the assistant subsystem (see §8–§10)
│   │   │   ├── service.py router.py tools.py context.py
│   │   │   ├── hybrid.py retrieval.py rerank.py query_expand.py
│   │   │   ├── guardrails.py prompts.py pricing.py menu_adapter.py
│   │   │   ├── vision.py voice.py
│   │   │   ├── embeddings/    # provider, vector_index, indexer, chunking, clip
│   │   │   └── eval/          # retrieval_eval.py + retrieval_metrics.json
│   │   └── seed/              # catalog_generator, seed, seed_kb, category_guides,
│   │                          #  product_guides, pdf_ingest, image_provider, placeholder_svg
│   ├── migrations/versions/    # Alembic chain
│   ├── tests/                  # unit / api / golden
│   ├── requirements.txt        # LEAN deployed set
│   └── requirements-dev.txt
└── frontend/
    ├── src/
    │   ├── App.tsx main.tsx
    │   ├── pages/  components/  context/  store/  hooks/  lib/  types/
    └── vite.config.ts  package.json  tailwind.config.js
```

---

## 5. Data model

All tables use string UUID primary keys and a `TimestampMixin` (`created_at`, `updated_at`).
The `EmbeddingType` column type maps to **pgvector `Vector(dim)`** on PostgreSQL and to a
**JSON array** on SQLite, so the same models support both backends.

```
 users ──< refresh_tokens
   │  └──< carts ──< cart_items ──< cart_item_options
   │  └──< orders ──< order_items ──< order_item_options
   │  └──< conversations ──< messages
   │  └──< user_preferences
   │  └──< conversation_feedback
 categories ──< menu_items ──< option_groups ──< option_choices
                   │  >──< dietary_tags   (M:N)
                   │  >──< allergens      (M:N)
                   ├──── product_embeddings        (1:1, text vector, 384-d)
                   └──── product_image_embeddings  (1:1, CLIP visual, 512-d)
 documents ──< document_chunks   (chunk text + 384-d embedding)
 audit_logs   (standalone, actor/action/target/detail)
```

**Aggregate groups**

- **Auth/users** — `User` (role: `customer | store_helper | manager | admin`, `is_active`),
  `RefreshToken` (hashed `jti` + token, rotation, revoke).
- **Catalog** — `Category`, `MenuItem` (slug, sku, `price_cents`, `cost_cents` COGS,
  `stock_qty`, `is_available`, `featured`, `image_url`, `keywords` JSON), `OptionGroup` /
  `OptionChoice` (configurable add-ons), `DietaryTag`, `Allergen` (repurposed retail flags
  e.g. *flammable, contains-battery, heavy-item, sharp-blade*).
- **Cart/orders** — `Cart` (user **or** `session_id` guest, `conversation_id` + `source` for
  chat attribution), `CartItem(+Option)`; `Order` (guest-capable, `payment_status`,
  `stripe_payment_intent_id`, `amount_paid_cents`, immutable `*_snapshot` line items).
- **Chat** — `Conversation` (`summary` for session memory, token totals), `Message` (role,
  content, `tool_payload`, `grounded_item_ids`/`grounded_doc_ids`, `model`, `route`,
  per-turn token counts, `tools_used`, `guardrail_violation`).
- **Knowledge/embeddings** — `Document` / `DocumentChunk` (heading-aware chunks + 384-d
  vector), `ProductEmbedding` (text, 384-d), `ProductImageEmbedding` (CLIP, 512-d).
- **Memory/feedback/audit** — `UserPreference` (key/value, `source`: stated|inferred|chat),
  `ConversationFeedback` (CSAT 1–5, one per conversation), `AuditLog`.

---

## 6. Backend core: auth, security, RBAC

Located in `backend/app/core/`.

**Authentication (`security.py`, `deps.py`).** Stateless **JWT access tokens** (HS256, 30-min
TTL) in an httponly cookie, plus **refresh tokens** (httponly, 7-day, scoped to
`/api/v1/auth`) that are **hashed in the DB and rotated on every refresh** (the old `jti` is
revoked). Passwords are hashed with **Argon2**. The frontend transparently retries a 401 once
through `POST /auth/refresh`.

**CSRF.** Double-submit cookie: a readable `csrf_token` cookie is matched against an
`x-csrf-token` header on every state-mutating request (timing-safe compare). GETs are exempt.

**RBAC.** A role rank `customer < store_helper < manager < admin` is enforced by dependency
factories: `require_staff`, `require_manager`, `require_admin`. An **`Actor`** abstraction
unifies logged-in users and guests (via an `x-session-id` header) and provides an IDOR
ownership check (`actor.owns(...)`) so guests can only see their own carts/orders.

**Rate limiting & lockout.** `slowapi` limiter (memory:// dev, redis:// prod) — 20/min chat,
10/min auth, 200/min default. A per-email lockout blocks for 15 min after 5 failed logins in
a 15-min window.

**Errors.** A small exception hierarchy (`AppError → NotFound/Forbidden/Auth`) renders a
uniform `{"error": {code, message, request_id}}` body; a request-id is attached to every
response for traceability.

**Cookie policy** is environment-aware: `Secure` + `SameSite=None` in production (so the app
works embedded in the HF Spaces iframe over HTTPS), `SameSite=Lax` in dev.

---

## 7. HTTP API reference

All routes are under `/api/v1`. **[CSRF]** = state-mutating, requires the CSRF header.
**[role]** = minimum role.

**Auth** (`/auth`)
| Method · Path | Purpose |
| --- | --- |
| `POST /register` · `POST /login` | Create account / authenticate (sets cookies). Rate-limited 10/min; login has per-email lockout. |
| `POST /refresh` · `POST /logout` | Rotate tokens / revoke + clear cookies. |
| `GET /me` | Current user (hydrates the SPA). |
| `GET /csrf` | Issue a CSRF token + cookie. |

**Menu** (`/menu`)
| Method · Path | Purpose |
| --- | --- |
| `GET /` | Paginated list; filters `q, category, dietary[], exclude_allergen[], available_only`. |
| `GET /{slug}` | Single product. |
| `GET /categories` | Categories **that have products** (empty ones are filtered out). |
| `GET /{slug}/recommendations` | Co-purchase + content-similar items. |
| `POST /by-ids` | Hydrate a list of product ids (used to render chat shortlists). |

**Cart** (`/cart`, all **[CSRF]**, `Actor`) — `GET /`, `POST /items`, `PATCH /items/{id}`,
`DELETE /items/{id}`, `DELETE /` (works for guests via session id).

**Orders** (`/orders`, `Actor`) — `POST /` **[CSRF]** create from cart (guest email allowed),
`GET /` my orders **[customer]**, `GET /{id}` with IDOR guard.

**Chat** (`/chat`) — `POST /stream` **[CSRF]** SSE assistant turn (optional auth; guests via
`x-session-id`; moderation + injection checks; 20/min); `POST /{id}/feedback` **[CSRF]** CSAT;
`GET /{id}` history; `DELETE /{id}`.

**Admin** (`/admin`, **[admin]**, **[CSRF]**) — menu CRUD (`POST/PATCH/DELETE /menu`), order
status (`PATCH /orders/{id}/status`), user management; every change is audited.

**Analytics** (`/analytics`, **[manager]**) — `inventory`, `margins`, `ai-attribution`,
`chat-eval`, `ai-ops`, `csat` (all accept a `days` window).

**Payments** (`/payments`) — `POST /create-intent` **[CSRF]**, `POST /webhook`
(Stripe-signature verified, no auth), `POST /confirm/{id}` **[CSRF]**, `GET /status/{id}`,
`POST /refund/{id}` **[manager] [CSRF]**.

**Media** (`/media`) — `GET /placeholder.svg` (public, cached SVG product tiles),
`POST /find-by-image` (vision product search), `POST /transcribe` (STT; 503 if unconfigured),
`POST /ocr-stock` **[staff]** + `POST /stock/apply` **[staff]** (handwritten count-sheet OCR
→ confirm → audited stock write).

---

## 8. The AI assistant subsystem

Located in `backend/app/ai/`. A chat turn is a **streaming, tool-calling loop** with a model
router in front and a deterministic validator behind.

```
 user message ─────────────────────────────────────────────────────────────┐
                                                                            │
 ┌── router.classify_turn() ────────────────────────────────────────────┐  │
 │  • multimodal (image present)      → MULTIMODAL → Sonnet              │  │
 │  • project keywords / length / Haiku micro-classifier → SIMPLE|COMPLEX│  │
 │     SIMPLE  → Haiku (cheap)        COMPLEX → Sonnet (heavy)           │  │
 └──────────────────────────────────────────────────────────────────────┘  │
                              │ picks one model for the turn                 │
                              ▼                                              │
 ┌── service.stream_chat() : tool-use loop (≤ 6 rounds) ───────────────────┐ │
 │  build memory preamble (saved prefs, fenced) + grounded user message    │ │
 │  while not final:                                                       │ │
 │    Claude responds → either tool_use blocks or final text               │ │
 │    execute tools (tools.py) → append results → accumulate grounded data │ │
 │  accumulate grounded_items / grounded_chunks BEFORE emitting any token  │ │
 └─────────────────────────────────────────────────────────────────────────┘ │
                              │                                              │
 ┌── guardrails (post-generation) ─────────────────────────────────────────┐ │
 │  validate_response(): every claimed price must match a grounded price    │ │
 │     (allows qty × unit-price line totals); else replace with SAFE_FALLBACK│ │
 │  validate_citations(): policy claim without a grounded chunk → soft note  │ │
 └─────────────────────────────────────────────────────────────────────────┘ │
                              │ SSE events: meta · delta · validated · done · error
                              ▼                                              │
 frontend renders streamed markdown, shortlist chips, CSAT widget ◀─────────┘
```

**Model router (`router.py`).** Classifies each turn cheaply: an image forces `MULTIMODAL`
(→ Sonnet); obvious project phrases ("paint my", "tile my", "build a", "renovate") force
`COMPLEX`; very short asks are `SIMPLE`; ambiguous mid-length asks get a **4-token Haiku
micro-classification** (fails safe to `SIMPLE`). The chosen route + model is recorded on the
message for observability. Toggle with `model_router_enabled`.

**Tools (`tools.py`).** The assistant is given a focused toolset; each executor returns
structured, *grounded* data (real DB rows), never free text the model could invent:

| Tool | What it does |
| --- | --- |
| `search_products` | Hybrid product search (lexical + vector + visual, filters). |
| `search_knowledge_base` | Hybrid KB search; auto-decomposes comparison queries (multi-hop). |
| `get_order_history` / `reorder` | Read past orders; re-add a prior purchase (fuzzy id/sku/name match). |
| `get_preferences` / `set_preference` | Persistent user memory (injection-checked values). |
| `compute_materials` | Project planner — BOM from room dimensions (paint/tile/laminate/drywall). |
| `add_materials_to_cart` | Batch-add a computed/suggested list. |
| `suggest_complementary` / `recommend_similar` / `frequently_bought_with` | Cross-sell / upsell from curated anchors + real co-purchase data. |

A `ToolContext` carries the db session, menu snapshot, user/session/conversation ids, and
loaded preferences so tools can attribute chat→cart→order and personalize.

**Memory & token budget.** Saved preferences are injected as a fenced preamble each turn.
Conversations carry running token totals and a one-line `summary`; a per-conversation token
budget (`max_tokens_per_conversation`) bounds cost. Pricing per model is estimated in
`pricing.py` and surfaced in AI-Ops.

**Multimodal.** `vision.py` — photo → short catalog search phrase (`/media/find-by-image`),
handwritten count-sheet OCR (`/media/ocr-stock`), and manual/spec-sheet OCR → Markdown for KB
ingestion. `voice.py` — pluggable STT (OpenAI/Groq Whisper) behind `/media/transcribe`,
returning 503 (not a fake transcript) when unconfigured. All vision/voice parsing is
defensive and never raises into the request.

---

## 9. Hybrid retrieval (RAG)

Located in `app/ai/hybrid.py`, `retrieval.py`, `rerank.py`, `query_expand.py`,
`embeddings/`. Retrieval fuses up to three independent "arms" with **Reciprocal Rank Fusion**
(`score(d) = Σ 1/(k + rank(d))`, `k=60`):

```
 query
   ├── LEXICAL arm    tokenize → score (name×3, keyword/category×2, desc×1; singularization)
   ├── VECTOR arm     embed query (fastembed BGE-small, 384-d) → ANN over *_embeddings
   └── VISUAL arm     CLIP text-embed → cosine over product_image_embeddings (512-d)
            │             (optional; returns [] without torch → fuser unchanged)
            ▼
        RRF fuse  ──►  (optional) re-rank wider candidate pool  ──►  top-k
                         cross-encoder if torch, else feature re-ranker
```

- **Exact-SKU fast path** promotes a queried SKU to rank 0 deterministically.
- **Embeddings (`embeddings/provider.py`).** `fastembed` BGE-small (384-d) by default; a
  pure-Python **hash-embedding** fallback keeps the vector arm populated where onnxruntime
  can't load (set `EMBEDDING_PROVIDER=hash` to force it). `vector_index.py` uses pgvector's
  `<=>` operator on Postgres and an in-memory NumPy cosine on SQLite. `indexer.py` embeds in
  batches of 256 and is content-hash idempotent. HNSW indexes (Postgres) accelerate ANN.
- **Re-ranker (`rerank.py`).** After fusion, an optional re-ranker re-scores a wider pool for
  precision: a sentence-transformers **cross-encoder** when torch is present, otherwise a
  deterministic **feature re-ranker** (term coverage 0.5 · heading match 0.25 · exact 2-gram
  0.15 · rank prior 0.10). Measured lift on the labeled KB set: hit@5 0.86→0.93, MRR
  0.54→0.59, nDCG 0.60→0.63. Toggle with `rerank_enabled`.
- **Query expansion (`query_expand.py`).** Comparison questions ("X vs Y", "difference
  between X and Y") are split into sub-queries, each retrieved independently and RRF-fused —
  so both sides of a comparison are well covered (multi-hop). An optional Haiku decomposer
  handles fuzzier phrasing.
- **Chunking (`embeddings/chunking.py`).** Markdown is split on H2/H3 headings into
  ~256-token windows with 32-token overlap; the heading is retained for citation
  (`Title › Section`).

The whole pipeline has an **offline evaluation harness** (see §14) so retrieval changes are
measured, not guessed.

---

## 10. Guardrails

Two independent layers ensure the assistant is grounded (`app/ai/guardrails.py`):

1. **Prompt rules** (`SYSTEM_PROMPT_RETAIL`): only discuss products/policies returned by
   tools; never invent prices; on a no-match, search again broader and offer a real in-stock
   alternative; cite policies as `Title › Section`; ground buying advice in the KB.
2. **Deterministic output validator** (`validate_response`): regex-extracts every price the
   model *claims*, distinguishes threshold phrasing ("under $5") from assertions ("it's
   $49.99"), and checks each claimed price against the **grounded** items for that turn
   (allowing qty × unit-price line totals, and prices already validated earlier in the
   conversation). On a mismatch the turn is replaced with `SAFE_FALLBACK` and
   `guardrail_violation` is recorded. `validate_citations` adds a *soft* disclaimer if a
   policy is mentioned without a grounding chunk.

This means even if the model hallucinated a price, the user never sees it — the safety net is
code, not a prompt.

---

## 11. Catalog, knowledge base & images

**Catalog generation (`seed/catalog_generator.py`).** Deterministic, seeded generation of a
realistic catalog from 19 categories × ~10–12 product types × variant **axes** (VOLT, GRADE,
SIZE, PACK, AMP, WATT, …) × brands × editions. `catalog_target=None` yields a curated ~1.2k
catalog; `catalog_target=N` scales to 10k+. SKUs are `BR-{CODE}-{NNNNN}`; prices derive from a
base × axis multipliers; stock is distributed (~8% out, ~17% low). **Truncation is
round-robin across categories**, so a small target (e.g. `CATALOG_TARGET=3000`) still covers
*every* category evenly instead of dropping trailing ones. The curated set lives in root
`menu_data.py`.

**Knowledge base (`seed/seed_kb.py`, `category_guides.py`, `product_guides.py`,
`pdf_ingest.py`).** Markdown policy/FAQ/warranty/shipping docs are ingested as
`Document`+`DocumentChunk`; plus ~195 per-type **buying guides** and ~19 richer per-category
guides (with spec-comparison **tables**, how-to-choose, safety, care). `pdf_ingest.py`
(optional `pypdf`/`reportlab`) ingests PDFs/spec-sheets page-by-page, and `ingest_image_manual`
OCRs a photographed manual into the KB — both reuse the same chunk pipeline.

**Product images (`seed/placeholder_svg.py`, `image_provider.py`, `api/media.py`).** Rather
than ship thousands of files or put random scenic stock photos on hardware, every product
gets a **branded SVG placeholder** rendered on the fly by `GET /media/placeholder.svg?cat&label`:
a per-category accent color + one of 19 distinct line icons (drill, hammer, screw, key, car,
pot, bulb, …) + the product label + a "BuildRight" wordmark, cached immutably for a year.
Zero image files, deterministic, offline, scales to any catalog size. Licensed photos
(Unsplash/Pexels) remain an opt-in path (`use_placeholder_images=False`).

---

## 12. Payments (Stripe)

Test-mode Stripe checkout via `services/payment_service.py` and `api/routers/payments.py`.

```
 checkout ─► POST /payments/create-intent ─► create pending Order + Stripe PaymentIntent
          ◄─ { client_secret, publishable_key, order_id }
 Stripe Elements (frontend) confirms card with client_secret
          ─► Stripe ─► POST /payments/webhook (signature-verified) ─► mark Order paid
 fallback ─► POST /payments/confirm/{id} re-fetches the PI and reconciles status
 manager  ─► POST /payments/refund/{id} (audited)
```

Money handling is integer-cents end-to-end; amounts/currency are validated server-side; the
webhook is the source of truth with `confirm` as a reconciliation fallback. Refunds are
manager-gated and audited.

---

## 13. Observability & analytics

Every assistant message persists telemetry: chosen `model`, `route`, per-turn input/output
tokens, `tools_used`, and `guardrail_violation`. Manager dashboards (`services/analytics_service.py`,
`/analytics/*`) expose:

- **AI-Ops** — cost (via `pricing.py`), routing mix (Haiku vs Sonnet), guardrail-violation
  rate, recent turn traces.
- **AI attribution** — revenue from chat-sourced carts/orders (via `Cart.source` /
  `Order.source` + `conversation_id`).
- **Chat-eval** — offline faithfulness / relevance / context-use scores (`eval_service.py`).
- **CSAT** — 1–5 ratings with histogram and recent comments.
- **Inventory & margins** — stock health and COGS-based profit (using `cost_cents`).

Everything user/admin-impacting is also written to `audit_logs`.

---

## 14. Retrieval evaluation

**Retrieval evaluation (`ai/eval/retrieval_eval.py`).** Pure metric functions — `hit@k`,
`MRR`, `nDCG@k` — over labeled question→doc sets (14 KB, 10 product). `evaluate_kb` /
`evaluate_products` measure the live pipeline (with/without re-rank) and write
`retrieval_metrics.json`. This harness was built *first*, so every retrieval change is
quantified rather than guessed (e.g. the re-ranker's measured lift, §9).

> **A note on fine-tuning.** Model routing (Haiku vs Sonnet) is intentionally handled by a
> cheap heuristic + a 4-token Haiku micro-classification — the task is simple enough that a
> trained classifier wouldn't earn its dependency or latency cost. Transformer fine-tuning is
> therefore scoped to a *separate, dedicated project* (where a proper labeled dataset and a
> held-out evaluation can do it justice), not bolted onto this app. PyTorch still appears here,
> but only behind the optional CLIP visual arm (§9) and the cross-encoder re-ranker (§9),
> each with a deterministic CPU fallback.

---

## 15. Frontend architecture

A Vite + React 18 + TypeScript SPA (`frontend/`). In dev, Vite proxies `/api` and `/health`
to the backend (`:8000`); in prod the same paths are same-origin.

**Routing & pages (`App.tsx`, `pages/`).** `/` Home (catalog + filters + chat + shortlist),
`/item/:slug`, `/about`, `/how-to-test`, `/login`, `/register`, `/checkout`, `/order/:id`,
`/orders` **[auth]**, `/manager` **[manager]**, `/admin` **[admin]**, `*` NotFound.
`ProtectedRoute` enforces role gates client-side (server is the real authority).

**Key components.** `layout/Navbar` (role-aware nav), `menu/FilterBar` + `menu/MenuCard`
(uses `imageSrc` with an `onError` fallback), `cart/CartDrawer`, and the **`chat/ChatWidget`** —
text + voice (MediaRecorder → `/media/transcribe`) + image (→ `/media/find-by-image`),
consumes the SSE stream, renders markdown (react-markdown + DOMPurify), shows a "what we
remember" panel for logged-in users, surfaces assistant **shortlists** back onto the
storefront, and collects CSAT.

**API layer (`lib/api/`).** A `client.ts` fetch wrapper adds the `x-session-id` header, fetches
+ attaches CSRF on writes, sends cookies, and transparently refreshes once on 401. `endpoints.ts`
groups typed calls (auth/menu/cart/orders/payments/media/analytics/admin/chat). `chatStream.ts`
parses SSE events (`meta`, `delta`, `validated`, `done`, `error`).

**State.** `AuthProvider` (React context, hydrates via `/auth/me`) for user/role; **Zustand**
`uiStore` for UI flags + shortlist + guest session id; **React Query** for server state (cart,
menu) with sane defaults; a `ToastProvider` for notifications.

---

## 16. Configuration reference

All settings (pydantic-settings, `app/core/config.py`) are env-overridable. Highlights:

| Group | Keys (default) |
| --- | --- |
| **Required** | `ANTHROPIC_API_KEY`, `SECRET_KEY` (prod: ≥32 chars, rejects known weak defaults) |
| **Database** | `DATABASE_URL` (`sqlite:///./cutdry.db` → `postgresql+psycopg://…`) |
| **Auth** | `ACCESS_TOKEN_EXPIRE_MINUTES`=30, `REFRESH_TOKEN_EXPIRE_DAYS`=7, `ALGORITHM`=HS256, `ADMIN_EMAIL`, `ADMIN_PASSWORD` |
| **Environment** | `ENVIRONMENT`=development\|production\|test (drives cookie `Secure`/`SameSite`), `CORS_ORIGINS` |
| **Rate limit** | `RATE_LIMIT_STORAGE`=memory://, `CHAT_RATE_LIMIT`=20/minute, `AUTH_RATE_LIMIT`=10/minute |
| **LLM / router** | `LLM_MODEL`=claude-haiku-4-5, `LLM_MODEL_HEAVY`=claude-sonnet-4-6, `LLM_ROUTER_MODEL`=claude-haiku-4-5, `MODEL_ROUTER_ENABLED`=true, `LLM_MAX_TOKENS`=400, `LLM_TEMPERATURE`=0.0 |
| **RAG** | `EMBEDDING_PROVIDER`=fastembed\|hash, `EMBEDDING_MODEL`=BAAI/bge-small-en-v1.5, `EMBEDDING_DIM`=384, `RAG_TOP_K`=12, `KB_TOP_K`=4, `RRF_K`=60, `RERANK_ENABLED`=true, `VISUAL_SEARCH_ENABLED`=true |
| **Catalog/images** | `CATALOG_TARGET` (None\|e.g. 3000\|10000), `IMAGE_PROVIDER`=placeholder, `USE_PLACEHOLDER_IMAGES`=true, `UNSPLASH_ACCESS_KEY`, `PEXELS_API_KEY` |
| **Voice** | `STT_PROVIDER`=""\|openai\|groq, `STT_API_KEY`, `STT_MODEL` |
| **Conversation** | `MAX_TOKENS_PER_CONVERSATION`=50000, `MAX_MESSAGES_PER_CONVERSATION`=100, `ENABLE_MODERATION`=false |
| **Stripe** | `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_CURRENCY`=cad |

---

## 17. Database migrations

Alembic chain (`backend/migrations/versions/`), additive and dialect-aware:

```
1e4d86e1f9ed  baseline (all core tables; pgvector extension on Postgres)
f158c824f9b7  cost_cents (COGS) + cart/order conversation_id + source (attribution)
020524e025ca  role tiers (customer → store_helper/manager/admin)
5cde14885b8b  guest orders (nullable user_id, session_id, guest_email)
7f3a9c2b1d4e  message telemetry (model, route, token counts, tools_used, guardrail_violation)
b2c4d6e8f0a1  conversation_feedback (CSAT)
c3d5e7f9a1b3  conversation.summary (session memory)
d4e6f8a0b2c4  pgvector HNSW indexes (Postgres only; no-op on SQLite)
e5f7a9b1c3d5  product_image_embeddings (CLIP visual, 512-d)
```

SQLite migrations use `batch_alter_table`; Postgres-only steps (HNSW, pgvector) no-op on
SQLite. CI runs the suite against **both** backends to prove the abstraction holds.

---

## 18. Testing & CI

**~267 tests** across three tiers (`backend/tests/`): **unit** (retrieval, RRF, router,
guardrail/pricing, query-expand, rerank, vision/CLIP, catalog scale, placeholders, eval
metrics), **api** (auth/RBAC/CSRF, chat stream, menu/search, cart/orders, guest checkout,
refunds, analytics, CSAT, media/voice), and **golden** (retrieval quality + validator
regression). Fixtures (`conftest.py`) build a temp SQLite DB once per session with **no real
API keys** (`ANTHROPIC_API_KEY=test-…`, `STT_PROVIDER=""`, placeholder images), so the suite
is fully **keyless and deterministic**; live-only tests are skipped.

**CI (`.github/workflows/ci.yml`)** runs four jobs on every push/PR: `secret-scan`
(gitleaks), `backend` (ruff + pytest, keyless), `backend-postgres` (same tests against a real
Postgres 16 + pgvector service), and `frontend` (build + vitest). `deploy-hf.yml` mirrors the
repo to the Hugging Face Space on push to `main`.

---

## 19. Deployment

**Single Docker image (`Dockerfile`).** Multi-stage: stage 1 builds the SPA with Node; stage
2 (`python:3.11-slim`) installs the lean backend deps, copies the built SPA, sets
`EMBEDDING_PROVIDER=hash`, `CATALOG_TARGET=3000`, `ENVIRONMENT=production`, **seeds at
startup**, then runs Uvicorn on `:8000`. FastAPI serves the SPA and API from one origin.

**Hugging Face Spaces (free).** The root `README.md` YAML header declares `sdk: docker`,
`app_port: 8000`. Push the repo to the Space; set secrets (`ANTHROPIC_API_KEY`, `SECRET_KEY`,
admin creds, optional Stripe/STT); HF rebuilds and seeds on boot. Storage is ephemeral —
fine, because seed-at-startup reproduces the dataset; attach Neon/Supabase Postgres + pgvector
for persistence by setting `DATABASE_URL`.

**Cloud (`docs/CLOUD_DEPLOY.md`).** The same image runs on Cloud Run / ECS / Fly. `docker-compose.yml`
provides a local prod-like stack: Postgres+pgvector, Redis (rate limit), MinIO (S3-compatible).
Only `DATABASE_URL`, `RATE_LIMIT_STORAGE`, and secrets change between targets.

---

## 20. Local development

```bash
# Backend (from backend/)
python -m venv .venv && . .venv/Scripts/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
echo "ANTHROPIC_API_KEY=sk-..." > .env
echo "SECRET_KEY=$(python -c 'import secrets;print(secrets.token_urlsafe(48))')" >> .env
python -m app.seed                  # create + seed the dev SQLite DB
uvicorn app.main:app --reload       # http://127.0.0.1:8000

# Frontend (from frontend/)
npm install
npm run dev                         # http://127.0.0.1:5173 (proxies /api → :8000)

# Tests
cd backend && pytest -q
cd frontend && npx vitest run && npm run build
```

Optional extras (never required for the core app):
`pip install -r app/seed/requirements-ingest.txt` (PDF ingest),
`-r app/ai/embeddings/requirements-multimodal.txt` (CLIP visual arm + cross-encoder re-ranker).

---

## 21. Key design decisions

- **One origin, one container.** FastAPI serves the SPA + API together — no CORS, no
  cross-site cookies, one thing to deploy. Trades a little separation for big operational
  simplicity (ideal for a free Space).
- **Guardrail as code, not prompt.** The deterministic price/citation validator is the real
  safety net; the prompt rules are the first line. A hallucinated price never reaches the user.
- **Cheap-by-default routing.** Haiku handles simple turns; Sonnet is reserved for complex /
  multimodal ones — measurably lower cost with no quality loss on hard turns.
- **Hybrid + measured retrieval.** Lexical catches exact terms/SKUs, vectors catch semantics,
  CLIP catches appearance; RRF fuses them, a re-ranker sharpens precision — and an eval
  harness proves each change helps.
- **Graceful degradation everywhere.** torch/CLIP/STT/cross-encoder/fastembed are all optional;
  each has a deterministic fallback that runs on a plain CPU box, so the deployed image stays
  lean and the test suite stays green.
- **Same code, SQLite ↔ Postgres.** `EmbeddingType` and `VectorIndex` abstract the vector
  store; CI runs against both, so "scale up" is a `DATABASE_URL` change, not a rewrite.
- **Deterministic, seed-at-startup data.** Generated catalog + placeholders + KB are
  reproducible and offline, so any environment boots into a complete, demoable state.

---

*Generated as the engineering single-source-of-truth for BuildRight AI. Keep it in sync with
the code — when a subsystem changes, update the matching section here.*
