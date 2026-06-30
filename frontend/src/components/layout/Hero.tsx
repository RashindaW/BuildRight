import type { ReactNode } from "react";

type Variant = "home" | "about" | "test";

const GLOW: Record<Variant, string> = {
  home: "#f59e0b",  // safety amber
  about: "#51647d", // steel
  test: "#f59e0b",
};

/** Shared industrial hero: a graphite→steel ground with a blueprint grid + accent glow.
 * One component, three variants, so Home / About / How-to-test read as a family. */
export function Hero({
  variant,
  eyebrow,
  title,
  subtitle,
  children,
}: {
  variant: Variant;
  eyebrow?: ReactNode;
  title: ReactNode;
  subtitle?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#0f172a] via-[#1e293b] to-[#0f172a] text-white shadow-pop">
      {/* Blueprint grid */}
      <svg className="pointer-events-none absolute inset-0 h-full w-full opacity-[0.16]" aria-hidden="true">
        <defs>
          <pattern id="hero-grid" width="28" height="28" patternUnits="userSpaceOnUse">
            <path d="M28 0H0V28" fill="none" stroke="#ffffff" strokeWidth="0.5" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#hero-grid)" />
      </svg>
      {/* Accent glow */}
      <div
        className="pointer-events-none absolute -right-20 -top-20 h-72 w-72 rounded-full opacity-30 blur-3xl"
        style={{ background: GLOW[variant] }}
        aria-hidden="true"
      />
      <div className="relative px-6 py-10 sm:px-10 sm:py-12">
        {eyebrow && (
          <div className="mb-3 inline-flex items-center gap-1.5 rounded-full border border-white/20 bg-white/5 px-3 py-1 text-xs font-medium tracking-wide text-white/80">
            {eyebrow}
          </div>
        )}
        <h1 className="max-w-3xl text-3xl font-bold tracking-tight sm:text-4xl">{title}</h1>
        {subtitle && <p className="mt-2 max-w-2xl text-sm text-white/80 sm:text-base">{subtitle}</p>}
        {children && <div className="mt-5">{children}</div>}
      </div>
    </div>
  );
}
