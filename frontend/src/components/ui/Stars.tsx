import { Star } from "lucide-react";

/** Read-only star rating display (rounds to the nearest whole star). */
export function Stars({
  value,
  count,
  size = 14,
  showValue = false,
  className = "",
}: {
  value: number;
  count?: number;
  size?: number;
  showValue?: boolean;
  className?: string;
}) {
  const rounded = Math.round(value);
  return (
    <span
      className={`inline-flex items-center gap-1 ${className}`}
      aria-label={`Rated ${value.toFixed(1)} out of 5`}
    >
      <span className="flex">
        {[1, 2, 3, 4, 5].map((i) => (
          <Star
            key={i}
            size={size}
            className={i <= rounded ? "fill-amber-400 text-amber-400" : "fill-gray-200 text-gray-200"}
            strokeWidth={0}
          />
        ))}
      </span>
      {showValue && <span className="text-xs font-semibold text-gray-700">{value.toFixed(1)}</span>}
      {count != null && <span className="text-xs text-gray-400">({count})</span>}
    </span>
  );
}

/** Interactive star input for the review form. */
export function StarInput({
  value,
  onChange,
  size = 24,
}: {
  value: number;
  onChange: (v: number) => void;
  size?: number;
}) {
  return (
    <div className="inline-flex items-center gap-1">
      {[1, 2, 3, 4, 5].map((i) => (
        <button
          key={i}
          type="button"
          onClick={() => onChange(i)}
          aria-label={`${i} star${i > 1 ? "s" : ""}`}
          className="rounded transition-transform hover:scale-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/50"
        >
          <Star
            size={size}
            className={i <= value ? "fill-amber-400 text-amber-400" : "fill-gray-200 text-gray-300"}
            strokeWidth={i <= value ? 0 : 1.5}
          />
        </button>
      ))}
    </div>
  );
}
