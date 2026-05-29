# Cut & Dry — Conversational Restaurant Ordering App

A professional, secure, full-stack online ordering app for a casual cafe, built around a **guardrailed AI menu assistant**. The assistant **never invents menu items, never guesses prices, and apologizes for anything off-menu** — and those guardrails are proven on every push by an automated, keyless test suite.

It began as a proof-of-concept (`answer_customer_query()` + a strict Claude prompt + 10 golden tests) and was extended into a FastAPI + React application: streaming multi-turn chat, menu browsing, cart & mock checkout, user accounts, an admin dashboard, and a full security posture.

```
React (Vite + Tailwind) SPA  ──REST + SSE──▶  FastAPI backend  ──▶  SQLite / PostgreSQL
        │                                          │
        └── streaming chat widget                  ├── AI core (guardrails preserved verbatim)
                                                    ├── auth (argon2 + cookie-JWT + CSRF + RBAC)
                                                    └── Anthropic Claude (claude-haiku-4-5)
```

---

## The three guardrails (the heart of the product)

1. **No invented items** — the assistant only discusses items in the retrieved menu.
2. **No guessed prices** — only prices that appear verbatim in the menu; never confirms a customer's asserted price ("is the burger $50?").
3. **Apologize for off-menu requests** — "I'm sorry, we don't currently offer that on our menu."

These live in `backend/app/ai/guardrails.py` as (a) the strict `SYSTEM_PROMPT` (moved verbatim from the PoC) and (b) a **deterministic output validator** that programmatically rejects any price not in the grounded set — so a fabricated price is blocked even if the model slips. During streaming, price-bearing chunks are **buffered until validated**, so a bad price never renders even for a frame.

---

## Quick start (Windows PowerShell)

### Prerequisites
Python 3.10+, Node 18+, Git. (Docker optional, for the Postgres swap.)

### 1. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt

# Create backend\.env  (NEVER commit this — it is gitignored)
#   ANTHROPIC_API_KEY=sk-ant-...
#   SECRET_KEY=<32+ random chars>
#   ADMIN_EMAIL=admin@cutdry.example.com
#   ADMIN_PASSWORD=<strong password>
#   ENVIRONMENT=development
# (See backend\.env.example for the template.)

python -m app.seed                 # create tables + load the 35-item menu + admin
uvicorn app.main:app --reload      # http://localhost:8000  (docs at /docs in dev)

# (optional) download matching menu photos — saved to frontend/public/img/menu/
# (gitignored; the seed auto-wires them). Re-run app.seed afterward to attach.
#   python ..\scripts\fetch_images.py ; python -m app.seed
```

### 2. Frontend

```powershell
cd frontend
npm install
npm run dev                        # http://localhost:5173  (proxies /api to :8000)
```

Open http://localhost:5173, sign up, browse the menu, chat with the assistant, and place an order.

> **Security note:** the Anthropic key is read **server-side only** and never shipped to the browser. The key that was committed during early development **should be rotated** in the Anthropic console; only placeholders live in the `.env.example` files.

---

## Testing

| Tier | Command (in `backend/`) | Needs API key? | Proves |
|---|---|---|---|
| Retrieval golden (GR) | `pytest tests/golden/test_golden_retrieval.py` | No | retrieval behaves like the PoC |
| Validator golden (GV) | `pytest tests/golden/test_golden_validator.py` | No | price-grounding guardrail |
| Unit + API | `pytest -m "not live"` | No | auth, IDOR, cart/orders, security headers, SSE wiring |
| Live golden (GL) | `python ..\golden_tests.py` | **Yes** | end-to-end guardrails, 10/10 |
| Frontend | `npm run test` (in `frontend/`) | No | components/format/sanitize |
| E2E | `npm run e2e` (in `frontend/`)¹ | Yes | order flow + chat guardrail in a browser |

¹ E2E needs both servers running and a one-time `npm i -D @playwright/test && npx playwright install chromium`.

Manual smoke (backend running on :8000): `pwsh scripts/smoke.ps1`.

---

## Prove the SQLite → PostgreSQL swap

```powershell
$env:ANTHROPIC_API_KEY="sk-ant-..."; $env:SECRET_KEY="<random>"
docker compose up --build      # api talks to Postgres with only DATABASE_URL changed
```

CI also runs the API suite against a Postgres service (`.github/workflows/ci.yml`).

---

## Features

- **AI assistant** — multi-turn, streaming (SSE), re-grounded every turn; inbound moderation + prompt-injection heuristics; per-conversation token caps; anonymous chat (with session id) or logged-in.
- **Menu** — 35 items across 10 categories; dietary tags, **allergens**, calories, spice level, modifiers (size/milk/add-ons with price deltas), search + filters.
- **Ordering** — cart, mock checkout with price snapshots, order history, order numbers.
- **Admin** — menu CRUD, order status workflow, user list, audit log; all behind `require_admin`.
- **Security** — argon2id passwords; JWT in httpOnly+SameSite cookies; CSRF double-submit; RBAC + IDOR guards; rate limiting; security headers + strict CORS; structured logs with secret/PII redaction; integer-cents money; no stack traces to clients.

## Repo layout

```
menu_data.py, golden_tests.py     # v1 source of truth + back-compat guardrail gate
backend/app/{core,models,schemas,api/routers,ai,safety,services,seed}/
backend/tests/{unit,api,golden}/
frontend/src/{pages,components,lib,hooks,context,store,types}/
docker-compose.yml, backend/Dockerfile, .github/workflows/ci.yml, scripts/smoke.ps1
```

## License

MIT — see [LICENSE](./LICENSE).
