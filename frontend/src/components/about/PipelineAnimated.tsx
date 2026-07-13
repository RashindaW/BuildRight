import { useEffect, useState } from "react";
import { Bot, Cpu, MessageCircle, ShieldCheck, Wrench } from "lucide-react";

/** Animated "what happens when you ask" pipeline — a pulse travels through the five
 * stages, lighting each one with its explanation. Pure CSS/React, loops forever. */

const STAGES = [
  { icon: MessageCircle, title: "You ask", body: "Any question — products, projects, policies. Text, photo, or voice." },
  { icon: Cpu, title: "Router picks a brain", body: "A cheap classifier sends simple turns to the fast model; complex ones escalate." },
  { icon: Wrench, title: "Tools fetch real data", body: "Catalog search, project planner, recommender — grounded rows, never guesses." },
  { icon: ShieldCheck, title: "Guardrail checks", body: "Every price is validated in code against grounded data before it renders." },
  { icon: Bot, title: "You get the answer", body: "Streamed live, with sources — and products you can add to the cart." },
];

const STEP_MS = 2200;

export function PipelineAnimated() {
  const [active, setActive] = useState(0);

  useEffect(() => {
    const reduced = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reduced) return;
    const t = setInterval(() => setActive((a) => (a + 1) % STAGES.length), STEP_MS);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="card overflow-hidden p-5">
      {/* stage row */}
      <div className="flex items-start justify-between gap-1">
        {STAGES.map((s, i) => {
          const Icon = s.icon;
          const isActive = i === active;
          const done = i < active;
          return (
            <div key={s.title} className="flex min-w-0 flex-1 flex-col items-center text-center">
              <div className="flex w-full items-center">
                <div className={`h-0.5 flex-1 rounded transition-colors duration-500 ${i === 0 ? "opacity-0" : done || isActive ? "bg-accent" : "bg-gray-200"}`} />
                <button
                  onClick={() => setActive(i)}
                  aria-label={s.title}
                  className={`grid h-11 w-11 shrink-0 place-items-center rounded-full border-2 transition-all duration-300 ${
                    isActive
                      ? "scale-110 border-accent bg-brand-800 text-accent shadow-pop"
                      : done
                        ? "border-accent/50 bg-brand-700 text-white/90"
                        : "border-gray-200 bg-white text-gray-400"
                  }`}
                >
                  <Icon size={18} />
                </button>
                <div className={`h-0.5 flex-1 rounded transition-colors duration-500 ${i === STAGES.length - 1 ? "opacity-0" : done ? "bg-accent" : "bg-gray-200"}`} />
              </div>
              <div className={`mt-2 text-[11px] font-semibold leading-tight sm:text-xs ${isActive ? "text-brand-800" : "text-gray-400"}`}>
                {s.title}
              </div>
            </div>
          );
        })}
      </div>

      {/* active stage explanation */}
      <div key={active} className="mt-4 animate-fade-in rounded-xl border border-brand-100 bg-brand-50/70 px-4 py-3 text-center">
        <p className="text-sm text-gray-700">{STAGES[active].body}</p>
      </div>
    </div>
  );
}
