import { useState } from "react";
import { ArrowUpRight, ChevronDown, CircleDollarSign, Cpu, ShieldAlert, ShieldCheck, Wrench, Zap } from "lucide-react";
import type { TraceStep } from "../../types";

const MODEL_BADGE: Record<string, { name: string; hint: string }> = {
  "claude-haiku-4-5": { name: "Haiku", hint: "fast, economical model" },
  "claude-sonnet-4-6": { name: "Sonnet", hint: "heavyweight model for complex turns" },
};

const TOOL_LABEL: Record<string, string> = {
  search_products: "Catalog search",
  search_menu: "Catalog search",
  search_knowledge_base: "Policy & guides",
  get_order_history: "Order history",
  reorder: "Reorder",
  get_preferences: "Preferences",
  set_preference: "Saved preference",
  compute_materials: "Project planner",
  add_materials_to_cart: "Cart update",
  suggest_complementary: "Cross-sell",
  recommend_similar: "Similar items",
  frequently_bought_with: "Bought together",
  get_inventory: "Inventory",
  get_margins: "Margins",
  get_ai_attribution: "AI attribution",
  get_ai_ops: "AI operations",
  get_csat: "CSAT",
  get_chat_quality: "Chat quality",
};

function shortModel(model?: string) {
  if (!model) return "Model";
  return MODEL_BADGE[model]?.name ?? model.replace(/^claude-/, "").split("-")[0];
}

/** Glass-box "How I answered" strip: the routing decision, each tool call, and the
 * guardrail check — rendered as live-appearing chips under an assistant message. */
export function AgentTracePanel({ trace, live }: { trace: TraceStep[]; live?: boolean }) {
  const [open, setOpen] = useState(false);
  if (!trace.length) return null;

  // On a cascade, the second attempt's route/tool/guardrail steps are the real story;
  // show the escalation chip plus the post-escalation steps.
  const lastEscIdx = trace.map((t) => t.type).lastIndexOf("escalation");
  const effective = lastEscIdx >= 0 ? trace.slice(lastEscIdx) : trace;
  const escalation = lastEscIdx >= 0 ? trace[lastEscIdx] : undefined;
  const route = effective.find((t) => t.type === "route") ?? trace.find((t) => t.type === "route");
  const tools = effective.filter((t) => t.type === "tool");
  const guard = [...trace].reverse().find((t) => t.type === "guardrail");
  const cost = [...trace].reverse().find((t) => t.type === "cost");
  const cache = trace.find((t) => t.type === "cache" && t.hit);

  return (
    <div className="mt-1.5 max-w-[85%] text-left">
      <button
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-1 text-[11px] font-medium text-gray-400 transition-colors hover:text-gray-600"
        aria-expanded={open}
      >
        <Zap size={11} className="text-accent-600" />
        How I answered
        {route && <span className="text-gray-500">· {shortModel(route.model)}</span>}
        {tools.length > 0 && <span className="text-gray-500">· {tools.length} tool{tools.length > 1 ? "s" : ""}</span>}
        {guard && (guard.ok ? <ShieldCheck size={11} className="text-success" /> : <ShieldAlert size={11} className="text-danger" />)}
        <ChevronDown size={11} className={`transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {(open || live) && (
        <div className="mt-1 flex flex-wrap gap-1">
          {cache && (
            <span
              className="badge animate-fade-in-up border border-accent/40 bg-accent-light text-accent-700"
              title="Served instantly from the semantic answer cache — prices re-validated against the live catalog"
            >
              <Zap size={11} /> Instant · cached
            </span>
          )}
          {route && route.model !== "semantic-cache" && (
            <span
              className="badge animate-fade-in-up border border-brand-200 bg-brand-50 text-brand-700"
              title={MODEL_BADGE[route.model ?? ""]?.hint ?? route.model}
            >
              <Cpu size={11} /> {shortModel(route.model)}
              {route.label && <span className="font-normal opacity-70">· {route.label}</span>}
              {typeof route.predicted_difficulty === "number" && (
                <span className="font-normal opacity-60" title="learned difficulty (0 easy → 1 hard)">
                  · d={route.predicted_difficulty.toFixed(2)}
                </span>
              )}
            </span>
          )}
          {escalation && (
            <span
              className="badge animate-fade-in-up border border-warning/40 bg-warning-light text-warning-dark"
              title={`First answer failed the guardrail on ${shortModel(escalation.from)} — retried on ${shortModel(escalation.to)}`}
            >
              <ArrowUpRight size={11} /> 2nd opinion: {shortModel(escalation.to)}
            </span>
          )}
          {tools.map((t, i) => (
            <span key={i} className="badge animate-fade-in-up border border-gray-200 bg-gray-50 text-gray-600">
              <Wrench size={11} /> {TOOL_LABEL[t.name ?? ""] ?? t.name}
              {typeof t.ms === "number" && <span className="font-normal opacity-60">{t.ms}ms</span>}
            </span>
          ))}
          {guard && (
            <span
              className={`badge animate-fade-in-up border ${
                guard.ok
                  ? "border-success/30 bg-success-light text-success-dark"
                  : "border-danger/30 bg-danger-light text-danger-dark"
              }`}
              title="Every price is validated against grounded catalog data before it renders"
            >
              {guard.ok ? <ShieldCheck size={11} /> : <ShieldAlert size={11} />}
              {guard.ok
                ? `Prices verified${guard.prices_checked ? ` (${guard.prices_checked})` : ""}`
                : "Guardrail blocked"}
            </span>
          )}
          {cost && typeof cost.usd === "number" && (
            <span
              className="badge animate-fade-in-up border border-accent/40 bg-accent-light text-accent-700"
              title="This turn's model cost vs always using the heavyweight model"
            >
              <CircleDollarSign size={11} /> ${cost.usd.toFixed(4)}
              {(cost.saved_pct ?? 0) > 0 && <span className="font-normal">· saved {cost.saved_pct}%</span>}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
