import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { menuApi } from "../lib/api/endpoints";
import { FilterBar } from "../components/menu/FilterBar";
import { MenuCard } from "../components/menu/MenuCard";

export default function Home() {
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [dietary, setDietary] = useState<string[]>([]);

  const categories = useQuery({ queryKey: ["categories"], queryFn: menuApi.categories });
  const menu = useQuery({
    queryKey: ["menu", q, category, dietary],
    queryFn: () => menuApi.list({ q, category, dietary }),
  });

  const toggleDietary = (d: string) =>
    setDietary((cur) => (cur.includes(d) ? cur.filter((x) => x !== d) : [...cur, d]));

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <div className="mb-6 rounded-2xl bg-gradient-to-r from-brand-500 to-brand-700 p-8 text-white">
        <h1 className="text-3xl font-bold">BuildRight Hardware</h1>
        <p className="mt-1 opacity-90">Quality tools, honest answers. Ask our assistant about any product or store policy.</p>
      </div>

      <FilterBar
        categories={categories.data ?? []}
        q={q}
        category={category}
        dietary={dietary}
        onQ={setQ}
        onCategory={setCategory}
        onToggleDietary={toggleDietary}
      />

      {menu.isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="card h-72 animate-pulse bg-gray-100" />
          ))}
        </div>
      ) : menu.data && menu.data.items.length > 0 ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {menu.data.items.map((item) => (
            <MenuCard key={item.id} item={item} />
          ))}
        </div>
      ) : (
        <p className="py-12 text-center text-gray-500">No items match your filters.</p>
      )}
    </div>
  );
}
