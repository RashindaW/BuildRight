const ARCHITECTURE = String.raw`
┌──────────────────────────────────────────────────────────────────────┐
│  React SPA  (Vite · TypeScript · Tailwind · TanStack Query · Zustand) │
│  storefront · chat widget (text / 🎤 voice / 🖼️ image) · dashboards    │
└───────────────────────────┬──────────────────────────────────────────┘
                            │  REST + SSE  (single origin)
┌───────────────────────────▼──────────────────────────────────────────┐
│  FastAPI  (Python)                                                    │
│                                                                       │
│   ┌──────────────┐    ┌──────────────────────────────────────────┐   │
│   │ Model Router │ →  │  Tool-use loop  +  Guardrails            │   │
│   │ Haiku triage │    │  search · reorder · project planner ·    │   │
│   │  → Sonnet    │    │  recommender · vision · materials math   │   │
│   └──────────────┘    └──────────────────────────────────────────┘   │
│                                                                       │
│   Hybrid RAG (vector + keyword · RRF)   ·   Vision / OCR / Voice-STT  │
│   RBAC + JWT/CSRF   ·   Stripe payments + refunds   ·   MCP server    │
│   AI observability (cost · routing · tools)   ·   Chat-quality eval   │
└───────────────────────────┬──────────────────────────┬───────────────┘
                            │                          │
              ┌─────────────▼──────────┐   ┌───────────▼─────────────────┐
              │  SQLite / PostgreSQL    │   │  Anthropic Claude · Groq    │
              │  + pgvector embeddings  │   │  Whisper · Unsplash · Stripe│
              └─────────────────────────┘   └─────────────────────────────┘
`;

const CAPABILITIES: { title: string; points: string[] }[] = [
  {
    title: "Guardrailed AI assistant",
    points: [
      "Hybrid RAG (vector + keyword, Reciprocal Rank Fusion) over the catalog + a policy/FAQ knowledge base",
      "Deterministic price guardrail — never invents products, never guesses prices, cites policy before answering",
      "Streaming (SSE) tool-use loop with a price/citation check before any token renders",
    ],
  },
  {
    title: "Multi-agent model router",
    points: [
      "A cheap Haiku classifier triages every turn",
      "Simple lookups stay on Haiku; project planning / multimodal / complex turns escalate to Sonnet",
      "Guardrails identical regardless of which model answers",
    ],
  },
  {
    title: "Agentic skills (tools)",
    points: [
      "Product & policy search, reorder from history",
      "Conversational project planner: 'repair my room' → measurements → costed materials list → add to cart → upsell",
      "Recommender: frequently-bought-with (collaborative filtering) + content similarity",
    ],
  },
  {
    title: "Multimodal",
    points: [
      "🖼️ Find-this-item from a photo (Claude vision)",
      "📝 Handwritten stock-sheet OCR → confirm → audited stock update (staff)",
      "🎤 Voice ordering (Groq Whisper) → feeds the normal chat/reorder flow",
    ],
  },
  {
    title: "Commerce & access",
    points: [
      "5 RBAC tiers: guest · customer · staff · manager · admin",
      "Guest checkout (session-bound, IDOR-safe), Stripe test-mode payments + admin refunds",
      "Manager dashboards: inventory, profit/margin, AI-attributed sales",
    ],
  },
  {
    title: "Observability & quality",
    points: [
      "AI Operations panel: agent cost, route mix (Sonnet-escalation rate), tool usage, recent-turns trace",
      "Offline chat-quality eval: price-faithfulness, answer-relevance, context-utilization",
      "MCP server re-exposes read-only tools to external agents with boundary RBAC",
    ],
  },
];

const STACK = [
  "FastAPI", "SQLAlchemy 2.0", "Alembic", "PostgreSQL + pgvector / SQLite",
  "Anthropic Claude (Haiku + Sonnet)", "Groq Whisper", "React 18 + Vite",
  "TailwindCSS", "TanStack Query", "Zustand", "Stripe", "Docker", "Hugging Face Spaces",
];

const LOGINS = [
  { role: "Shopper", email: "demo@buildright.com", pass: "Demo1234!", note: "browse, chat, voice, image search, checkout" },
  { role: "Manager", email: "manager@buildright.com", pass: "ManagerDemo1234!", note: "dashboards + AI Operations + refunds" },
  { role: "Staff", email: "staff@buildright.com", pass: "StaffDemo1234!", note: "fulfilment + handwritten OCR stock intake" },
];

export default function About() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-6 rounded-2xl bg-gradient-to-r from-brand-500 to-brand-700 p-6 text-white sm:p-8">
        <h1 className="text-2xl font-bold sm:text-3xl">About BuildRight Hardware</h1>
        <p className="mt-1 max-w-2xl text-sm opacity-90 sm:text-base">
          A production-leaning, full-stack hardware store built around a guardrailed, multi-agent AI
          assistant — hybrid RAG, conversational project planning, multimodal (vision · voice · OCR),
          recommendations, payments, RBAC dashboards, and AI cost/quality observability.
        </p>
      </div>

      <section className="mb-8">
        <h2 className="mb-3 text-lg font-semibold">System architecture</h2>
        <div className="card overflow-x-auto p-4">
          <pre className="text-[11px] leading-tight text-gray-700 sm:text-xs">{ARCHITECTURE}</pre>
        </div>
      </section>

      <section className="mb-8">
        <h2 className="mb-3 text-lg font-semibold">Capabilities at a glance</h2>
        <div className="grid gap-4 md:grid-cols-2">
          {CAPABILITIES.map((c) => (
            <div key={c.title} className="card p-4">
              <h3 className="font-semibold text-brand-700">{c.title}</h3>
              <ul className="mt-2 space-y-1 text-sm text-gray-600">
                {c.points.map((p) => (
                  <li key={p} className="flex gap-2">
                    <span className="text-brand-500">▸</span>
                    <span>{p}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      <section className="mb-8">
        <h2 className="mb-3 text-lg font-semibold">Tech stack</h2>
        <div className="flex flex-wrap gap-2">
          {STACK.map((s) => (
            <span key={s} className="rounded-full bg-gray-100 px-3 py-1 text-sm text-gray-700">{s}</span>
          ))}
        </div>
      </section>

      <section className="mb-8">
        <h2 className="mb-1 text-lg font-semibold">Demo logins (for reviewers)</h2>
        <p className="mb-3 text-sm text-gray-500">
          Sign in to explore each access tier. This is a sandboxed demo — test data only, Stripe test
          mode, and it re-seeds on each deploy.
        </p>
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-gray-500">
              <tr>
                <th className="px-4 py-2">Role</th>
                <th className="px-4 py-2">Email</th>
                <th className="px-4 py-2">Password</th>
                <th className="px-4 py-2">What you can try</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {LOGINS.map((l) => (
                <tr key={l.email}>
                  <td className="px-4 py-2 font-medium">{l.role}</td>
                  <td className="px-4 py-2 font-mono text-xs">{l.email}</td>
                  <td className="px-4 py-2 font-mono text-xs">{l.pass}</td>
                  <td className="px-4 py-2 text-gray-500">{l.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-xs text-gray-400">
          Tip: ask the assistant "I want to paint my 12×10 room, what do I need?" to see the project
          planner, or use the 🖼️ / 🎤 buttons in the chat.
        </p>
      </section>
    </div>
  );
}
