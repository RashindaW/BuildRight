import { DIETARY_LABELS } from "../../lib/format";

const COLORS: Record<string, string> = {
  vegan: "bg-green-100 text-green-800 border-green-300",
  vegetarian: "bg-lime-100 text-lime-800 border-lime-300",
  "gluten-free": "bg-amber-100 text-amber-800 border-amber-300",
  "dairy-free": "bg-sky-100 text-sky-800 border-sky-300",
  "contains-nuts": "bg-red-100 text-red-800 border-red-300",
};

export function DietaryBadge({ tag }: { tag: string }) {
  const cls = COLORS[tag] ?? "bg-gray-100 text-gray-700 border-gray-300";
  return (
    <span className={`inline-block rounded-full border px-2 py-0.5 text-xs font-medium ${cls}`}>
      {DIETARY_LABELS[tag] ?? tag}
    </span>
  );
}
