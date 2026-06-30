/** Animated "the assistant is working" indicator with a live status label
 * (e.g. "Thinking…", "Searching the catalog…", "Summarizing…"). */
export function WorkingDots({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-gray-500">
      <span className="text-sm">{label}</span>
      <span className="flex gap-1">
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand-400 [animation-delay:-0.3s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand-400 [animation-delay:-0.15s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand-400" />
      </span>
    </span>
  );
}
