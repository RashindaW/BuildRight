/** Data for the About-page architecture slideshow. Diagrams are LaTeX/TikZ compiled to
 * committed SVGs under /public/diagrams (see docs/diagrams/). */
export interface ArchSlide {
  n: number;
  slug: string;
  title: string;
  subtitle: string;
  body: string;
  alt: string;
  src: string;
}

const make = (s: Omit<ArchSlide, "src">): ArchSlide => ({
  ...s,
  src: `/diagrams/slide-${String(s.n).padStart(2, "0")}-${s.slug}.svg`,
});

export const ARCH_SLIDES: ArchSlide[] = [
  make({
    n: 1, slug: "overview",
    title: "What BuildRight AI is, and the problem it solves",
    subtitle: "A hardware store where you can just ask, instead of hunting through 10,000 SKUs",
    body:
      "BuildRight is an online hardware store with a built-in AI shopping assistant. A do-it-yourself shopper faces thousands of near-identical products, dense policies, and how-to questions a search box can't really answer. Here you simply chat — “how much paint for a 12×10 room?”, “what's the return policy?” — and get the right product, a costed project plan, or a one-click reorder. Crucially, every answer is grounded in the real catalog and policy documents, so the assistant never invents a product or guesses a price.",
    alt:
      "A DIY shopper overwhelmed by 10k SKUs points to a central BuildRight AI assistant, which fans out to three outcomes: the right product fast, a costed project plan, and checkout & reorder — with a note that answers are grounded and never guess a price.",
  }),
  make({
    n: 2, slug: "architecture",
    title: "High-level architecture: one app, three layers",
    subtitle: "A React single-page app talks to one FastAPI process that fronts data and AI",
    body:
      "The whole product is one deployable unit. The browser runs a React single-page app that talks to a single FastAPI process over plain REST plus a streaming channel (SSE) for live chat — and because FastAPI serves both the app and the API from one origin, there are no cross-site cookie or CORS headaches. Behind FastAPI sit three lanes: a services layer (cart, orders, memory), the AI subsystem (router, tools, retrieval), and external APIs (Claude, Stripe). Everything persists through one SQLAlchemy data layer that runs on SQLite locally and Postgres + pgvector in the cloud, unchanged.",
    alt:
      "A top-down stack: Browser React SPA connects by a two-way REST + SSE arrow to a FastAPI single-origin box, which fans down to Services, the AI subsystem, and External APIs, all flowing into one SQLAlchemy ORM box over SQLite (dev) / Postgres + pgvector (prod).",
  }),
  make({
    n: 3, slug: "hybrid-rag",
    title: "Hybrid retrieval: three searchers, fused and re-ranked",
    subtitle: "Keyword, meaning, and appearance combined with Reciprocal Rank Fusion, then sharpened",
    body:
      "To find the right answer, the system runs up to three independent searchers in parallel: a lexical arm that matches exact names, keywords and SKUs; a vector arm that captures meaning using 384-dimension embeddings; and an optional visual arm that matches a product's appearance via CLIP. Their rankings are merged with Reciprocal Rank Fusion — a voting scheme where items ranked highly by several arms float to the top. A re-ranker then re-scores a wider pool for precision (a measured lift from hit@5 0.86 to 0.93). Each arm is independent, so if a heavy dependency is absent the rest keep working.",
    alt:
      "A query splits into three parallel arms — lexical (names/SKUs), vector (384-d embeddings), and an optional CLIP visual arm — which feed an RRF fusion box, then a re-ranker, then a Top-k box.",
  }),
  make({
    n: 4, slug: "agent-loop",
    title: "The guardrailed agent loop and model router",
    subtitle: "A cheap router picks the model; tools fetch real data; a code guardrail checks every price",
    body:
      "Every chat turn first hits a model router: a fast, cheap Haiku triage sends simple lookups to Haiku and escalates complex or image turns to Sonnet — so you only pay for the big model when the question earns it. The chosen model then runs a tool-use loop (up to six rounds), calling real tools — product/policy search, project planner, reorder, recommender — that return grounded database rows, never free-form guesses. Before any answer reaches you, a deterministic guardrail validates every claimed price and citation against that grounded data; a mismatch is replaced with a safe fallback. The safety net is code, not just a prompt.",
    alt:
      "A user turn flows into a model router (Haiku triage) that branches to Haiku (simple) or Sonnet (complex/image), both feeding a tool-use loop (search, planner, reorder, recommend, ≤6 rounds), which drops into a guardrail validator (price & citation check) before a grounded answer.",
  }),
  make({
    n: 5, slug: "recommender-graph",
    title: "The recommender: a co-purchase graph that propagates",
    subtitle: "Products that sell together form a graph; signal spreads across it into recommendations",
    body:
      "Recommendations come from a graph, not a hard-coded list. Each product is a node, and every time two items are bought together an edge connects them, building a co-purchase graph. A graph neural network then propagates signal along those edges — each product effectively learns from its neighbours and their neighbours — producing an embedding that captures “things that belong in the same job”. From those embeddings the assistant surfaces complete-the-job add-ons and close substitutes (buy a drill, get bits, anchors and screws).",
    alt:
      "Four product nodes (drill, bits, anchors, screws) connected by edges in a co-purchase graph feed a graph-propagation (GNN message passing) box, then item embeddings, then a recommendations box of complete-the-job and similar items.",
  }),
  make({
    n: 6, slug: "multimodal",
    title: "Multimodal: photo, voice, and handwriting",
    subtitle: "Images, speech, and count sheets all become inputs to the same grounded pipeline",
    body:
      "You're not limited to typing. A photo of a tool is read by Claude Vision and turned into a catalog search phrase; spoken requests are transcribed by Whisper into text. Both then flow into exactly the same grounded search, chat, and knowledge-base pipeline as typed queries — one engine, many doorways. Separately, staff can photograph a handwritten stock count sheet; OCR reads the numbers, the worker confirms, and the stock update is written and audited.",
    alt:
      "Three inputs — Photo, Voice, Count sheet — go to Claude Vision, Whisper STT, and OCR; Vision and Whisper converge into the same grounded pipeline (search, chat, knowledge base), while OCR flows to an audited stock update staff confirm.",
  }),
  make({
    n: 7, slug: "commerce",
    title: "Commerce: roles, guest checkout, and Stripe",
    subtitle: "Five access tiers guard a webhook-verified payment flow with audited refunds",
    body:
      "Access is governed by five role tiers — guest, customer, staff, manager, admin — enforced on the server, with guests safely scoped to their own cart and orders. Checkout creates a pending order and a Stripe PaymentIntent; the browser confirms the card, and Stripe's signature-verified webhook is the source of truth that marks the order paid (a confirm call reconciles if the webhook is delayed). Money is handled in integer cents end to end. Refunds are restricted to managers and written to the audit log.",
    alt:
      "An RBAC bar (guest, customer, staff, manager, admin) sits above a left-to-right payment flow: Cart, create-intent (pending order), Stripe PaymentIntent, signature-verified webhook, Order PAID — with a refund branch marked manager & audited.",
  }),
  make({
    n: 8, slug: "observability",
    title: "Observability and evaluation: nothing is guessed",
    subtitle: "Every turn logs telemetry feeding manager dashboards and an offline quality harness",
    body:
      "Every assistant turn writes a telemetry record: which model and route it used, tokens consumed, tools called, and whether a guardrail fired. That stream powers manager dashboards — AI-Ops (cost and Haiku-vs-Sonnet routing mix), AI attribution (revenue traced back to chat), and CSAT ratings. In parallel, an offline evaluation harness scores retrieval and answer quality with real metrics (hit@k, MRR, nDCG, faithfulness), so every change is measured rather than guessed — which is what lets the team prove, for example, that the re-ranker actually helped.",
    alt:
      "Every chat turn writes a telemetry record (model, route, tokens, tools, guardrail) that fans out to AI-Ops, AI attribution, and CSAT dashboards, and down to an offline eval harness (hit@k, MRR, nDCG, faithfulness).",
  }),
  make({
    n: 9, slug: "deployment",
    title: "Tech stack and deployment: one image, runs anywhere",
    subtitle: "A multi-stage Docker build self-seeds and runs free on Spaces or any cloud",
    body:
      "The whole app ships as a single Docker image. A Node stage builds the React front end, then a Python stage runs FastAPI that serves both that front end and the API. On boot the container seeds itself — catalog, knowledge base, and embeddings — so even an ephemeral host comes up fully searchable. The same image runs free on Hugging Face Spaces or on Cloud Run, ECS, or Fly, and switching from local SQLite to Postgres + pgvector is a single environment variable.",
    alt:
      "A build pipeline: Stage 1 Node builds the React SPA; Stage 2 Python runs FastAPI serving the SPA + API; producing one Docker image that seeds at startup and deploys to HF Spaces or Cloud Run / ECS / Fly, with SQLite → Postgres + pgvector via one env var.",
  }),
];
