# BuildRight AI — 10-minute Showcase pitch

**Audience:** Vector MLA reviewers (technical lead + functional manager) + non-technical stakeholders.
**Theme to echo:** *"Empowering AI to generate, reason, and act with autonomy."* Position as an
**Intelligent Search & Assistants + Personalization & Customer Experience** PoC.
**One-liner:** *"BuildRight AI is a guardrailed, multi-agent shopping assistant that turns a hardware
store's 10,000-SKU catalog and policy library into a conversation that never invents a product or a price."*

**Timing:** ~3 min demo, ~7 min narrative. Lead with the problem + a live demo; keep slides sparse.

---

### Slide 1 — Title / hook (0:00–0:45)
- **BuildRight AI — the smart hardware store.** Live: `rashindaw-buildright.hf.space`.
- Hook: *"A shopper asks 'what do I need to paint my 12×10 room?' — most stores make them figure it out. Watch ours answer with a costed materials list, grounded in real stock and prices, in one turn."*

### Slide 2 — The business problem (0:45–1:30)
- Hardware retail: huge SKU counts, non-expert shoppers, repetitive staff load ("where is it / how do I choose / is it in stock"), abandoned carts, thin baskets.
- **Framed as an AI problem:** deflect routine questions, lift basket size (recommendations + project planning), and **measure** the lift — without ever giving a wrong price (trust is the product).
- Constraints I designed for: small-business data readiness, low budget, low latency.

### Slide 3 — Solution overview (1:30–2:15)
- An **agentic assistant** embedded in a full store: search, plan a project, reorder, recommend, check policy, pay — by talking.
- Cohort anchors, all live: **Foundation Models · Prompt Engineering · RAG · Agentic tool use** + memory, multimodal.
- *"I owned this end-to-end: framing → build → evaluation → deploy → docs."*

### Slide 4 — Architecture (2:15–3:00)  *(show the `/about` diagram)*
- React SPA → FastAPI (single origin) → SQLite/**Postgres+pgvector**.
- **Model router** (cheap Haiku triages → escalate to Sonnet) → **tool-use loop** (11 tools) → **guardrails**.
- Hybrid RAG (vector + keyword, RRF) · Vision/OCR/Voice · RBAC · Stripe · observability.

### Slide 5 — LIVE DEMO (3:00–5:30)  *(the core — rehearse this)*
Run these in order (also on `/how-to-test`):
1. **Grounded search:** *"cheapest cordless drill?"* → real SKU + exact price. *(RAG + guardrail)*
2. **Missing item → proactive alternative:** *"do you sell a laser level?"* → apologizes, offers the closest in-stock item. *(guardrail + agentic re-search)*
3. **Buying guide (semantic):** *"impact driver vs hammer drill?"* → cited advice. *(RAG over generated knowledge)*
4. **Project planner (agent):** *"paint my 12×10 room, 8ft walls"* → costed materials list → add to cart. *(reasoning + tool use)*
5. **Multimodal:** 🖼️ photo → matching product; 🎤 voice → order. *(vision + STT)*
6. **Manager view:** `/manager` → **AI Operations** (cost, route mix, tools, guardrail rate) + **CSAT**. *(MLOps + value)*

### Slide 6 — How it works (AI techniques) (5:30–6:45)
- **RAG:** lexical + vector arms fused with Reciprocal Rank Fusion over catalog + policy + ~195 buying guides.
- **Multi-agent routing:** Haiku classifies the turn; only complex/multimodal turns pay for Sonnet → **cost-optimized**.
- **Retrieval, measured:** an eval harness scores hit@k / MRR / nDCG, so a re-ranker's lift is quantified, not guessed.
- **Memory:** preferences captured + injected; per-conversation need-summary; "what we remember" panel.

### Slide 7 — Evaluation & trust (6:45–7:45)  *(the differentiator)*
- **Deterministic price guardrail:** every `$` in an answer is validated against retrieved data — a fabricated price is *blocked*, not just discouraged. (Two layers: prompt + code backstop.)
- **Offline chat-quality eval:** faithfulness / answer-relevance / context-utilization per turn.
- **CSAT loop:** 1–5 rating → manager dashboard.
- **244+ automated tests**, migrations checked on SQLite **and** Postgres.

### Slide 8 — Business value + observability (7:45–8:45)
- **AI-attributed revenue** (orders the assistant drove) + **margin** + **CSAT** on the manager dashboard.
- **AI Operations**: per-turn **$ cost**, Haiku→Sonnet escalation rate, tool usage, guardrail-block rate — runtime ROI/quality at a glance.
- Story: *"It's not just a chatbot — it tells the business what it costs and what it earns."*

### Slide 9 — Delivery & deployment (8:45–9:30)
- **Deployed live, free** on Hugging Face Spaces (Docker, single-origin, seeds at startup); **CI** runs tests + `tsc` + migration check on every push; **continuous deploy** loop.
- **Cloud-ready:** GCP Cloud Run / AWS ECS is config-not-rewrite (`docs/CLOUD_DEPLOY.md`).
- **For two audiences:** `/about` + `/how-to-test` for non-technical reviewers; `docs/VECTOR_MLA.md` + tests for technical.

### Slide 10 — Roadmap + close (9:30–10:00)
- Next: managed Postgres+pgvector, object-store/CDN images, Sentry/OTel, Ragas LLM-judge eval gate, the LangGraph migration (designed).
- Close: *"A small-business AI problem, framed and shipped end-to-end: an evaluated, guardrailed, cost-aware PoC with a clean handover — exactly the embedded-MLA loop."*

---

## Demo script (verbatim prompts)
`cheapest cordless drill?` · `do you sell a laser level?` · `what's the difference between an impact
driver and a hammer drill?` · `I want to paint my bedroom, it's 12 by 10 feet with 8 foot walls` →
**Add to cart** → 🖼️/🎤 → log in `manager@buildright.com / ManagerDemo1234!` → `/manager`.

## Anticipated Q&A
- **Why not LangChain?** Hand-built the loop so the **price guardrail** + routing are fully controlled; LlamaIndex retriever included to show the integration.
- **Why Anthropic not OpenAI?** Provider-agnostic tool-use; Groq (OpenAI-compatible) used for Whisper — APIs are swappable.
- **Where's fine-tuning?** Deliberately *not* here — turn routing is simple enough that a heuristic + a 4-token Haiku call solve it cheaply, so a trained classifier wouldn't earn its keep. Transformer fine-tuning is scoped to a separate, dedicated project where a proper labeled dataset + held-out eval can do it justice.
- **Is it production?** Demo is on free HF; production gap is documented and config-level (managed DB, CDN, monitoring, secrets).
- **Hallucinated prices?** Structurally impossible to render — the deterministic validator blocks any ungrounded price.
- **Latency/cost?** Router keeps ~simple turns on Haiku; observability shows real per-turn $.

## What I personally owned (say this)
Problem framing · data/synthetic generation · RAG + agent design · **evaluation harness** ·
the trust/guardrail layer · full-stack build · deployment + CI · documentation for both audiences.
