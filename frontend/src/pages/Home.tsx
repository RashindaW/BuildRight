import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { menuApi } from "../lib/api/endpoints";
import { FilterBar } from "../components/menu/FilterBar";
import { MenuCard } from "../components/menu/MenuCard";
import { useUiStore } from "../store/uiStore";

type SortKey = "relevance" | "price-asc" | "price-desc" | "name";

export default function Home() {
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [dietary, setDietary] = useState<string[]>([]);
  const [sortBy, setSortBy] = useState<SortKey>("relevance");

  const shortlistedItemIds = useUiStore((s) => s.shortlistedItemIds);
  const clearShortlist = useUiStore((s) => s.clearShortlist);

  const categories = useQuery({ queryKey: ["categories"], queryFn: menuApi.categories });
  const menu = useQuery({
    queryKey: ["menu", q, category, dietary],
    queryFn: () => menuApi.list({ q, category, dietary }),
  });
  const shortlist = useQuery({
    queryKey: ["shortlist", shortlistedItemIds],
    queryFn: () => menuApi.byIds(shortlistedItemIds),
    enabled: shortlistedItemIds.length > 0,
  });

  const sortedShortlist = useMemo(() => {
    const items = shortlist.data ? [...shortlist.data] : [];
    if (sortBy === "price-asc") items.sort((a, b) => a.price_cents - b.price_cents);
    else if (sortBy === "price-desc") items.sort((a, b) => b.price_cents - a.price_cents);
    else if (sortBy === "name") items.sort((a, b) => a.name.localeCompare(b.name));
    return items; // "relevance" keeps the assistant's order
  }, [shortlist.data, sortBy]);

  const toggleDietary = (d: string) =>
    setDietary((cur) => (cur.includes(d) ? cur.filter((x) => x !== d) : [...cur, d]));

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <div className="mb-6 rounded-2xl bg-gradient-to-r from-brand-500 to-brand-700 p-6 text-white sm:p-8">
        <h1 className="text-2xl font-bold sm:text-3xl">BuildRight Hardware</h1>
        <p className="mt-1 text-sm opacity-90 sm:text-base">Quality tools, honest answers. Ask our assistant about any product or store policy.</p>
      </div>

      {shortlistedItemIds.length > 0 && (
        <section className="mb-6 rounded-2xl border border-brand-200 bg-brand-50/60 p-4 sm:p-5">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-lg font-semibold">
              🛍️ Shortlisted by the assistant{" "}
              <span className="text-sm font-normal text-gray-500">({sortedShortlist.length})</span>
            </h2>
            <div className="flex items-center gap-3 text-sm">
              <label className="text-gray-600">
                Sort:{" "}
                <select
                  className="rounded-lg border border-gray-300 px-2 py-1"
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as SortKey)}
                >
                  <option value="relevance">Relevance</option>
                  <option value="price-asc">Price: low → high</option>
                  <option value="price-desc">Price: high → low</option>
                  <option value="name">Name</option>
                </select>
              </label>
              <button className="text-gray-500 hover:text-gray-800" onClick={clearShortlist}>
                Clear
              </button>
            </div>
          </div>
          {shortlist.isLoading ? (
            <div className="py-6 text-center text-sm text-gray-500">Loading…</div>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {sortedShortlist.map((item) => (
                <MenuCard key={item.id} item={item} />
              ))}
            </div>
          )}
        </section>
      )}

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
