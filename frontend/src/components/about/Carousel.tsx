import { useCallback, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { ARCH_SLIDES } from "./slides";

/** Step-by-step architecture slideshow: prev/next arrows, dot indicators, keyboard nav. */
export function Carousel() {
  const [i, setI] = useState(0);
  const n = ARCH_SLIDES.length;
  const go = useCallback((d: number) => setI((x) => Math.min(n - 1, Math.max(0, x + d))), [n]);
  const slide = ARCH_SLIDES[i];

  return (
    <div
      className="card overflow-hidden"
      role="group"
      aria-roledescription="carousel"
      aria-label="System architecture, step by step"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "ArrowLeft") {
          e.preventDefault();
          go(-1);
        } else if (e.key === "ArrowRight") {
          e.preventDefault();
          go(1);
        }
      }}
    >
      {/* Diagram stage */}
      <div className="relative border-b border-gray-200 bg-gradient-to-b from-white to-brand-50/60 p-4 sm:p-6">
        <img
          key={slide.src}
          src={slide.src}
          alt={slide.alt}
          className="mx-auto h-auto max-h-[360px] w-full max-w-3xl animate-fade-in object-contain"
        />
        <button
          onClick={() => go(-1)}
          disabled={i === 0}
          aria-label="Previous step"
          className="absolute left-2 top-1/2 grid h-10 w-10 -translate-y-1/2 place-items-center rounded-full border border-gray-200 bg-white/90 text-brand-700 shadow-card backdrop-blur transition hover:bg-white disabled:opacity-30 sm:left-3"
        >
          <ChevronLeft size={20} />
        </button>
        <button
          onClick={() => go(1)}
          disabled={i === n - 1}
          aria-label="Next step"
          className="absolute right-2 top-1/2 grid h-10 w-10 -translate-y-1/2 place-items-center rounded-full border border-gray-200 bg-white/90 text-brand-700 shadow-card backdrop-blur transition hover:bg-white disabled:opacity-30 sm:right-3"
        >
          <ChevronRight size={20} />
        </button>
      </div>

      {/* Caption */}
      <div className="p-5 sm:p-6" aria-live="polite">
        <div className="text-xs font-semibold uppercase tracking-wide text-accent-700">
          Step {i + 1} of {n}
        </div>
        <h3 className="mt-1 text-lg font-bold tracking-tight text-gray-900 sm:text-xl">{slide.title}</h3>
        <p className="mt-0.5 text-sm font-medium text-brand-600">{slide.subtitle}</p>
        <p className="mt-3 text-sm leading-relaxed text-gray-600">{slide.body}</p>
      </div>

      {/* Controls */}
      <div className="flex items-center justify-between gap-3 border-t border-gray-200 bg-gray-50/70 px-4 py-3 sm:px-5">
        <button onClick={() => go(-1)} disabled={i === 0} className="btn-ghost btn-sm disabled:opacity-40">
          <ChevronLeft size={14} /> Back
        </button>
        <div className="flex flex-wrap items-center justify-center gap-1.5">
          {ARCH_SLIDES.map((s, idx) => (
            <button
              key={s.n}
              onClick={() => setI(idx)}
              aria-label={`Go to step ${idx + 1}: ${s.title}`}
              aria-current={idx === i}
              className={`h-2 rounded-full transition-all ${
                idx === i ? "w-6 bg-brand-600" : "w-2 bg-gray-300 hover:bg-gray-400"
              }`}
            />
          ))}
        </div>
        <button onClick={() => go(1)} disabled={i === n - 1} className="btn-ghost btn-sm disabled:opacity-40">
          Next <ChevronRight size={14} />
        </button>
      </div>
    </div>
  );
}
