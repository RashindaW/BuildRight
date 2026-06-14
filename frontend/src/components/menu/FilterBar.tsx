import type { Category } from "../../types";

interface Props {
  categories: Category[];
  q: string;
  category: string;
  onQ: (v: string) => void;
  onCategory: (v: string) => void;
}

export function FilterBar({ categories, q, category, onQ, onCategory }: Props) {
  return (
    <div className="card mb-6 space-y-3 p-4">
      <input
        type="search"
        value={q}
        onChange={(e) => onQ(e.target.value)}
        placeholder="Search products…"
        className="w-full rounded-lg border border-gray-300 px-3 py-2"
        aria-label="Search products"
      />
      <div className="flex flex-wrap gap-2">
        <button
          className={`rounded-full px-3 py-1 text-sm ${category === "" ? "bg-brand-600 text-white" : "bg-gray-100"}`}
          onClick={() => onCategory("")}
        >
          All
        </button>
        {categories.map((c) => (
          <button
            key={c.slug}
            className={`rounded-full px-3 py-1 text-sm capitalize ${
              category === c.slug ? "bg-brand-600 text-white" : "bg-gray-100"
            }`}
            onClick={() => onCategory(c.slug)}
          >
            {c.name}
          </button>
        ))}
      </div>
    </div>
  );
}
