import { useEffect, useRef, useState } from "react";
import { Bot, CircleDollarSign, Cpu, ShieldCheck, Wrench } from "lucide-react";

/** Scripted, looping "watch the agent work" demo for the Home hero.
 * Pure frontend animation over canned data — zero API calls per visitor. */

interface Scenario {
  question: string;
  status: string;
  answer: string;
  chips: { icon: "cpu" | "wrench" | "shield" | "dollar"; label: string }[];
}

const SCENARIOS: Scenario[] = [
  {
    question: "How much paint do I need for a 12×10 bedroom?",
    status: "Planning your project…",
    answer:
      "For 12×10 ft with 8 ft walls you'll need 2 gallons — Premier Interior Eggshell, $42.99/gal. Want me to add everything to your cart?",
    chips: [
      { icon: "cpu", label: "Sonnet · complex" },
      { icon: "wrench", label: "Project planner" },
      { icon: "shield", label: "Prices verified" },
    ],
  },
  {
    question: "Do you have cordless drills under $100?",
    status: "Searching the catalog…",
    answer:
      "Yes — the Mastercraft 20V Cordless Drill/Driver is $89.99 and in stock. It pairs well with a 100-pc bit set.",
    chips: [
      { icon: "cpu", label: "Haiku · routed cheap" },
      { icon: "wrench", label: "Catalog search" },
      { icon: "shield", label: "Prices verified" },
      { icon: "dollar", label: "saved 79%" },
    ],
  },
  {
    question: "What's your return policy on power tools?",
    status: "Checking our policies & guides…",
    answer:
      "Power tools can be returned within 30 days with receipt — Returns & Refunds Policy › Return Window. Opened tools are exchange-only.",
    chips: [
      { icon: "cpu", label: "Haiku · fast" },
      { icon: "wrench", label: "Policy & guides" },
      { icon: "shield", label: "Cited answer" },
    ],
  },
];

const CHIP_ICON = { cpu: Cpu, wrench: Wrench, shield: ShieldCheck, dollar: CircleDollarSign };

// Phases: type question → thinking → stream answer → show chips → hold → next
export function HeroDemo() {
  const [scenario, setScenario] = useState(0);
  const [qChars, setQChars] = useState(0);
  const [aChars, setAChars] = useState(0);
  const [phase, setPhase] = useState<"typing" | "working" | "answering" | "done">("typing");
  const reduced = useRef(
    typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches,
  );

  const s = SCENARIOS[scenario];

  useEffect(() => {
    if (reduced.current) {
      setQChars(s.question.length);
      setAChars(s.answer.length);
      setPhase("done");
      const t = setTimeout(() => next(), 6000);
      return () => clearTimeout(t);
    }
    let t: ReturnType<typeof setTimeout>;
    if (phase === "typing") {
      if (qChars < s.question.length) t = setTimeout(() => setQChars((c) => c + 2), 40);
      else t = setTimeout(() => setPhase("working"), 250);
    } else if (phase === "working") {
      t = setTimeout(() => setPhase("answering"), 1100);
    } else if (phase === "answering") {
      if (aChars < s.answer.length) t = setTimeout(() => setAChars((c) => c + 3), 22);
      else t = setTimeout(() => setPhase("done"), 300);
    } else {
      t = setTimeout(() => next(), 4200);
    }
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase, qChars, aChars, scenario]);

  function next() {
    setScenario((i) => (i + 1) % SCENARIOS.length);
    setQChars(0);
    setAChars(0);
    setPhase("typing");
  }

  return (
    <div className="w-full max-w-sm rounded-xl2 border border-white/15 bg-white/5 p-3 backdrop-blur-sm" aria-hidden="true">
      <div className="mb-2 flex items-center gap-1.5 text-xs font-medium text-white/60">
        <Bot size={13} className="text-accent" /> BuildRight AI — live demo
      </div>

      {/* user bubble */}
      <div className="mb-2 flex justify-end">
        <div className="max-w-[85%] rounded-2xl bg-accent px-3 py-1.5 text-left text-xs font-medium text-brand-900">
          {s.question.slice(0, qChars)}
          {phase === "typing" && <span className="animate-pulse">▎</span>}
        </div>
      </div>

      {/* assistant bubble */}
      {phase !== "typing" && (
        <div className="flex justify-start">
          <div className="max-w-[92%] rounded-2xl bg-white/10 px-3 py-1.5 text-left text-xs text-white/90">
            {phase === "working" ? (
              <span className="inline-flex items-center gap-1.5 text-white/60">
                {s.status}
                <span className="flex gap-0.5">
                  <span className="h-1 w-1 animate-bounce rounded-full bg-accent [animation-delay:-0.3s]" />
                  <span className="h-1 w-1 animate-bounce rounded-full bg-accent [animation-delay:-0.15s]" />
                  <span className="h-1 w-1 animate-bounce rounded-full bg-accent" />
                </span>
              </span>
            ) : (
              <>{s.answer.slice(0, aChars)}</>
            )}
          </div>
        </div>
      )}

      {/* trace chips */}
      <div className="mt-2 flex min-h-[1.4rem] flex-wrap gap-1">
        {phase === "done" &&
          s.chips.map((c, i) => {
            const Icon = CHIP_ICON[c.icon];
            return (
              <span
                key={`${scenario}-${i}`}
                className="inline-flex animate-fade-in-up items-center gap-1 rounded-full border border-white/20 bg-white/10 px-2 py-0.5 text-[10px] font-medium text-white/80"
                style={{ animationDelay: `${i * 140}ms` }}
              >
                <Icon size={10} className={c.icon === "shield" ? "text-green-400" : "text-accent"} />
                {c.label}
              </span>
            );
          })}
      </div>
    </div>
  );
}
