/** BuildRight monogram + wordmark — a slate lettermark with a safety-amber rule.
 * Replaces the generic lucide-Bot lockup across the navbar and heroes. */
export function Wordmark({ onDark = false, className = "" }: { onDark?: boolean; className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <svg width="32" height="32" viewBox="0 0 32 32" aria-hidden="true" className="shrink-0">
        <defs>
          <linearGradient id="wm-grad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#3b4d63" />
            <stop offset="1" stopColor="#161e29" />
          </linearGradient>
        </defs>
        <rect width="32" height="32" rx="8" fill="url(#wm-grad)" />
        <text
          x="16"
          y="20"
          textAnchor="middle"
          fontFamily="Inter, system-ui, sans-serif"
          fontSize="16"
          fontWeight="800"
          fill="#ffffff"
        >
          B
        </text>
        <rect x="8" y="23.5" width="16" height="2.5" rx="1.25" fill="#f59e0b" />
      </svg>
      <span className={`text-lg font-bold tracking-tight ${onDark ? "text-white" : "text-gray-900"}`}>
        BuildRight <span className={onDark ? "text-accent" : "text-brand-600"}>AI</span>
      </span>
    </span>
  );
}
