import type { Category } from "../../types";

const DIETARY = ["vegan", "vegetarian", "gluten-free", "dairy-free"];

interface Props {
  categories: Category[];
  q: string;
  category: string;
  dietary: string[];
  onQ: (v: string) => void;
  onCategory: (v: string) => void;
  onToggleDietary: (v: string) => void;
}

export function FilterBar({ categories, q, category, dietary, onQ, onCategory, onToggleDietary }: Props) {
  return (
    <div className="card mb-6 space-y-3 p-4">
      <input
        type="search"
        value={q}
        onChange={(e) => onQ(e.target.value)}
        placeholder="Search the menu…"
        className="w-full rounded-lg border border-gray-300 px-3 py-2"
        aria-label="Search menu"
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
      <div className="flex flex-wrap gap-2">
        {DIETARY.map((d) => (
          <label key={d} className="flex items-center gap-1 text-sm">
            <input
              type="checkbox"
              checked={dietary.includes(d)}
              onChange={() => onToggleDietary(d)}
            />
            <span className="capitalize">{d.replace("-", " ")}</span>
          </label>
        ))}
      </div>
    </div>
  );
}
