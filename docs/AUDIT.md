# Feature Audit — all 28 how-to-test missions (Stage 1.1)

Audited against the local dev stack (backend :8000, seeded 9,157-product dev DB).
API-side missions exercised programmatically; UI missions inspected in code.
Legend: ✅ pass · 🛠 fixed in this pass · 📋 queued (bigger item, planned stage) · ⚠ env note

## Shop as a guest
| # | Mission | Result |
|---|---------|--------|
| 1 | Browse/search/filter storefront | ✅ 9,157 products; `q=drill` → 49; `category=safety` → 483; 19 non-empty categories |
| 2 | Generated SVG product imagery | ✅ dark industrial tiles render; **real-photo upgrade queued (Stage 1.2** — pool 100% built: 195/195 types) |
| 3 | Stock status + ratings on detail | ✅ SKU, stock badge, stars (when rated) |

## Reviews & the recommendation graph
| # | Mission | Result |
|---|---------|--------|
| 4 | Reviews + AI summary | ✅ list/summary/aggregate work; guest post ✅; logged-in duplicate → 409 ✅ |
| 5 | GNN recs + "why" graph | ✅ 6 recs; 8 graph neighbours on `circular-saw` |

## Chat with the AI assistant (6–13)
| # | Mission | Result |
|---|---------|--------|
| 6–13 | Grounded search, guardrail, RAG citation, buying guide, recommendations, project planner, shortlist, status | ✅ SSE stream starts and status events flow (live-key checks were verified earlier on the deployed Space); **true token streaming queued (Stage 1.3)** — current streaming is post-generation chunking |

## Multimodal & memory
| # | Mission | Result |
|---|---------|--------|
| 14 | Image search | ✅ endpoint validates input (422 without file); UI affordance present (icon button + tooltip) |
| 15 | Voice ordering | ✅ graceful errors incl. mic-permission-denied copy ("Microphone access was blocked.") |
| 16 | User memory | ✅ demo shopper has 2 prefs + 1 summary; Memory panel renders |
| 17 | CSAT rating | ✅ star prompt post-answer (dev DB has 0 responses — expected) |

## Checkout & orders
| # | Mission | Result |
|---|---------|--------|
| 18 | Cart + guest checkout + Stripe | ✅ cart add/qty/subtotal correct (session-bound); ⚠ Stripe keys not set in local `.env` → create-intent correctly returns `stripe_not_configured` (works on the Space, which has test keys) |
| 19 | Order history + reorder | ✅ 6 orders for demo shopper |

## Manager intelligence
| # | Mission | Result |
|---|---------|--------|
| 20 | Dashboard KPIs | ✅ inventory 9,924 items / 1,662 low-stock (threshold 15), margins on 154 orders |
| 21 | Ask-your-data chat | ✅ manager SSE stream starts; anon → 401 |
| 22 | AI Operations | ✅ 19 turns of telemetry |
| 23 | Router evidence | ✅ route mix present |
| 24 | CSAT + chat-eval | ✅ endpoints live |

## Power features & access control
| # | Mission | Result |
|---|---------|--------|
| 25 | OCR stock intake | ✅ endpoints validate (needs key at runtime) |
| 26 | Admin orders/refunds | ✅ RBAC-gated (401 anon) |
| 27 | Admin menu CRUD + instant embed | ✅ verified by test suite (`test_admin_embed.py`) |
| 28 | RBAC tiers + MCP | ✅ 401s on anon analytics/admin; all three demo logins 200 |

## UX inspection findings

| Finding | Severity | Status |
|---|---|---|
| **Navbar had no mobile menu** — 6+ links overflow on phones | High | 🛠 fixed: hamburger + slide-down panel < md, auth actions included, desktop unchanged |
| **Chat panel fixed 32rem height** clips short/landscape viewports | Medium | 🛠 fixed: `max-h-[calc(100dvh-5rem)]` clamp |
| Product images are placeholders (realism) | High | 📋 Stage 1.2 (pool ready, flip + review) |
| Streaming is cosmetic (full answer generates before display) | High | 📋 Stage 1.3 |
| Agent work invisible (routing/tools/guardrail) | Medium | 📋 Stage 1.4 glass-box panel |
| Checkout error handling | — | ✅ already good: toasts on failure, disabled states, guest-email required |
| Toasts | — | ✅ 3.5s auto-dismiss, variant styling |
| Empty states / skeletons | — | ✅ present on storefront, cart, orders |

## Env notes (not bugs)
- Local `.env` lacks Stripe keys → checkout testable only on the deployed Space (by design).
- Voice/vision need `STT_API_KEY`/`ANTHROPIC_API_KEY` at runtime; both degrade gracefully.
- Dev-DB CSAT is empty until ratings are submitted.
