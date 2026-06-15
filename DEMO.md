# BuildRight AI — Demo Guide

A ready-to-run demo of a retail store with a **guardrailed, hybrid-RAG AI assistant**.

## What's in the box

| | |
|---|---|
| **Products** | **1,207** across 20 categories, each with a unique **SKU** (`BR-XXX-NNNNN`), price, stock level, keywords, and tags |
| **Knowledge base** | **16 policy/FAQ documents** (returns, refunds, warranty, shipping, price-match, financing, gift cards, rewards, safety, assembly, …) chunked + embedded for cited answers |
| **Accounts** | 1 admin + 2 demo customers (with backdated order history for the memory/reorder demo) |
| **AI assistant** | hybrid retrieval (vector + keyword via RRF) over products **and** policies, SKU lookup, order memory, reorder, hard price guardrail, policy citations |

## Run it

```powershell
# 1. Backend (from backend/)
python -m app.seed                 # builds the full demo DB: 1207 products + KB + embeddings + accounts (~10s)
uvicorn app.main:app --reload      # http://localhost:8000  (API docs at /docs)

# 2. Frontend (from frontend/)
npm install                        # first time only
npm run dev                        # http://localhost:5173
```

Open http://localhost:5173 and click **💬 Ask us** (bottom-right) to chat with the Store Assistant.

## Accounts

| Role | Email | Password | Notes |
|---|---|---|---|
| **Admin** | `admin@cutdry.example.com` | from `ADMIN_PASSWORD` in `backend/.env` | catalog CRUD, order status, users, audit log |
| **Customer** | `demo@buildright.com` | `Demo1234!` | 3 past orders (paint, power tool, hand tool); prefers Mastercraft |
| **Customer (Pro)** | `pro@buildright.com` | `ProDemo1234!` | contractor; bulk building-materials orders |

> Log in as `demo@buildright.com` to demo **order history** and **reorder**. Anonymous chat works too (product + policy search), but memory features require login.

## Sample SKUs (for the SKU-lookup demo)

| SKU | Product | Price |
|---|---|---|
| `BR-PWR-98052` | Mastercraft 20V Cordless Drill/Driver | $49.99 |
| `BR-PWR-97665` | 7-1/4" Corded Circular Saw | $79.99 |
| `BR-HND-90448` | 20 oz Steel Claw Hammer | $18.99 |
| `BR-HVC-11025` | EverBrite 100W Garage Heater | $230.99 |
| `BR-PLM-10162` | AquaFlow Black Kitchen Faucet | $123.99 |

(Every product has a SKU — browse the catalog or ask the assistant "what's the SKU for …".)

## Demo script (paste these into the chat)

**1. SKU lookup (exact lexical match)**
> *What can you tell me about SKU BR-PWR-97665?*

→ Returns the Circular Saw with its exact price and stock. Try any SKU above.

**2. Semantic / need-based search (the vector arm)**
> *I need to keep my garage warm this winter — what do you have?*

→ Finds **garage heaters** even though the query shares no words with the product name. (Compare with a plain keyword search to see the hybrid blend.)

> *Something to cut plywood and lumber*  →  circular saws
> *My kitchen tap is leaking*  →  kitchen faucets

**3. Policy question with citation (RAG over the knowledge base)**
> *What's your return policy if my drill arrives defective?*

→ Answers from the policy docs and cites the source (e.g. *Returns & Refunds Policy › Damaged or Defective Items*). Ask follow-ups: *"How long for the refund?"*, *"Do you offer financing?"*

**4. Price guardrail (try to make it lie)**
> *Is the Mastercraft drill $500?*

→ The assistant will **not** confirm a fabricated price. A deterministic validator blocks any price not grounded in a real product, even mid-stream.

**5. Memory + reorder (log in as `demo@buildright.com` first)**
> *What did I order recently?*  →  lists real past orders
> *Reorder the paint*  →  adds it to the cart (the cart badge updates live)

**6. Out-of-catalog (graceful apology)**
> *Do you sell live sharks?*  →  polite "we don't carry that".

## Notes on the hybrid RAG

- **Two arms, fused by Reciprocal Rank Fusion (RRF):** a **keyword** arm (exact SKU + term scoring) and a **vector** arm (embeddings). SKU lookups are forced to an exact-match fast path.
- **Embeddings:** the default is local `fastembed` (`bge-small-en-v1.5`, real neural semantics, offline, no API key). If `fastembed`/`onnxruntime` can't load on the host, the provider **automatically falls back** to a deterministic feature-hashing bag-of-words embedding so the vector arm still works and the app runs everywhere — no config needed. On a host where fastembed loads, you get full neural semantics with **zero code change** (just re-run `python -m app.seed`).
- **Guardrails:** prices are hard-validated against grounded products (a fabricated price never renders); policy answers are softly required to cite a retrieved KB section.
