import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Layers } from "lucide-react";
import { menuApi } from "../lib/api/endpoints";
import { Hero } from "../components/layout/Hero";
import { Carousel } from "../components/about/Carousel";
import { PipelineAnimated } from "../components/about/PipelineAnimated";
import { CountUp } from "../components/ui/CountUp";

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
      "Recommendations: real co-purchase collaborative filtering plus content-similar alternatives",
    ],
  },
  {
    title: "Multimodal",
    points: [
      "Find-this-item from a photo (Claude vision)",
      "Handwritten stock-sheet OCR → confirm → audited stock update (staff)",
      "Voice ordering (Groq Whisper) → feeds the normal chat/reorder flow",
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
  const menu = useQuery({ queryKey: ["menu", "", ""], queryFn: () => menuApi.list({}) });
  const productCount = menu.data?.total ?? 0;

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <Hero
        variant="about"
        eyebrow={<><Layers size={13} /> How it's built</>}
        title="How BuildRight AI works"
        subtitle="A production-leaning, full-stack hardware store built around a guardrailed, multi-agent AI assistant — hybrid RAG, conversational project planning, multimodal (vision · voice · OCR), payments, RBAC dashboards, and AI cost/quality observability."
      />

      <div className="my-8 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-brand-200 bg-brand-50 px-4 py-3">
        <span className="text-sm text-brand-800">
          New here? Take the guided tour through every feature with copy-ready prompts.
        </span>
        <Link to="/how-to-test" className="btn-accent">Take the tour →</Link>
      </div>

      {/* Stat band — count-up on scroll; product count is live from the API */}
      <section className="mb-8 grid grid-cols-2 gap-4 md:grid-cols-4">
        {[
          { value: productCount, label: "Products in catalog", suffix: "" },
          { value: 0.93, label: "Retrieval hit@5 (measured)", decimals: 2, suffix: "" },
          { value: 289, label: "Automated tests", suffix: "" },
          { value: 5, label: "RBAC access tiers", suffix: "" },
        ].map((s) => (
          <div key={s.label} className="card p-4 text-center">
            <div className="text-2xl font-bold text-brand-700 sm:text-3xl">
              <CountUp value={s.value} decimals={s.decimals ?? 0} suffix={s.suffix} />
            </div>
            <div className="mt-1 text-xs text-gray-500">{s.label}</div>
          </div>
        ))}
      </section>

      <section className="mb-8">
        <h2 className="mb-1 text-lg font-semibold">What happens when you ask</h2>
        <p className="mb-3 text-sm text-gray-500">
          The five stages every question goes through — watch it run, or tap a stage.
        </p>
        <PipelineAnimated />
      </section>

      <section className="mb-8">
        <h2 className="mb-1 text-lg font-semibold">System architecture</h2>
        <p className="mb-3 text-sm text-gray-500">
          Step through how the product is built — use the arrows (or ← / → keys).
        </p>
        <Carousel />
      </section>

      <section className="mb-8">
        <h2 className="mb-3 text-lg font-semibold">Capabilities at a glance</h2>
        <div className="grid gap-4 md:grid-cols-2">
          {CAPABILITIES.map((c) => (
            <div key={c.title} className="card card-hover p-4">
              <h3 className="font-semibold text-brand-700">{c.title}</h3>
              <ul className="mt-2 space-y-1 text-sm text-gray-600">
                {c.points.map((p) => (
                  <li key={p} className="flex gap-2">
                    <span className="text-accent">▸</span>
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
          Sign in to explore each access tier. Test data only, Stripe test mode — the demo re-seeds on
          each deploy.
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
          planner, or use the image / voice buttons in the chat.
        </p>
      </section>
    </div>
  );
}
