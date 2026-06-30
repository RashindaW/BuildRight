import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Bot, FlaskConical, MessageCircle, PackageSearch, ShoppingBag } from "lucide-react";
import { menuApi } from "../lib/api/endpoints";
import { FilterBar } from "../components/menu/FilterBar";
import { MenuCard } from "../components/menu/MenuCard";
import { SkeletonCard } from "../components/ui/Skeleton";
import { EmptyState } from "../components/ui/EmptyState";
import { useUiStore } from "../store/uiStore";

type SortKey = "relevance" | "price-asc" | "price-desc" | "name";

export default function Home() {
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [sortBy, setSortBy] = useState<SortKey>("relevance");

  const shortlistedItemIds = useUiStore((s) => s.shortlistedItemIds);
  const clearShortlist = useUiStore((s) => s.clearShortlist);
  const setChatOpen = useUiStore((s) => s.setChatOpen);
  const showOnlyShortlist = useUiStore((s) => s.showOnlyShortlist);
  const setShowOnlyShortlist = useUiStore((s) => s.setShowOnlyShortlist);
  const onlyShortlist = showOnlyShortlist && shortlistedItemIds.length > 0;

  const categories = useQuery({ queryKey: ["categories"], queryFn: menuApi.categories });
  const menu = useQuery({
    queryKey: ["menu", q, category],
    queryFn: () => menuApi.list({ q, category }),
    enabled: !onlyShortlist, // skip the full catalog when focused on the shortlist
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

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <div className="mb-6 overflow-hidden rounded-2xl bg-gradient-to-br from-brand-600 via-brand-700 to-brand-800 text-white shadow-sm">
        <div className="flex items-center justify-center gap-1.5 bg-white/10 px-6 py-1.5 text-center text-xs font-medium tracking-wide">
          <FlaskConical size={13} /> Live demo — test data only · Stripe test mode · re-seeds on deploy
        </div>
        <div className="p-6 sm:p-8">
          <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight sm:text-3xl">
            <Bot size={28} /> BuildRight AI
          </h1>
          <p className="mt-1 text-base font-medium text-white sm:text-lg">
            The smart hardware store — ask, plan, and build with an AI that never guesses.
          </p>
          <p className="mt-1 max-w-xl text-sm opacity-80 sm:text-base">
            Search the catalog, get project plans and honest recommendations, and check store policies —
            grounded in real data, never invented items or prices.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {["Hybrid RAG", "Guardrailed", "Multi-agent router", "Multimodal"].map((c) => (
              <span key={c} className="badge bg-white/15 text-white">{c}</span>
            ))}
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              onClick={() => setChatOpen(true)}
              className="inline-flex items-center gap-1.5 rounded-lg bg-white px-4 py-2 text-sm font-semibold text-brand-700 shadow-sm transition hover:bg-brand-50 active:scale-[0.98]"
            >
              <MessageCircle size={16} /> Ask the assistant
            </button>
            <Link
              to="/how-to-test"
              className="rounded-lg border border-white/40 px-4 py-2 text-sm font-medium text-white hover:bg-white/10"
            >
              How to test →
            </Link>
          </div>
        </div>
      </div>

      {shortlistedItemIds.length > 0 && (
        <section className="mb-6 rounded-2xl border border-brand-200 bg-brand-50/60 p-4 sm:p-5">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h2 className="flex items-center gap-2 text-lg font-semibold">
              <ShoppingBag size={18} className="text-brand-600" /> Shortlisted by the assistant{" "}
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
              {onlyShortlist && (
                <button
                  className="text-brand-600 hover:text-brand-800"
                  onClick={() => setShowOnlyShortlist(false)}
                >
                  Show all products
                </button>
              )}
              <button className="text-gray-500 hover:text-gray-800" onClick={clearShortlist}>
                Clear
              </button>
            </div>
          </div>
          {shortlist.isLoading ? (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <SkeletonCard key={i} />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {sortedShortlist.map((item) => (
                <MenuCard key={item.id} item={item} />
              ))}
            </div>
          )}
        </section>
      )}

      {!onlyShortlist && (
        <>
          <FilterBar
            categories={categories.data ?? []}
            q={q}
            category={category}
            onQ={setQ}
            onCategory={setCategory}
          />

          {menu.isLoading ? (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <SkeletonCard key={i} />
              ))}
            </div>
          ) : menu.data && menu.data.items.length > 0 ? (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {menu.data.items.map((item) => (
                <MenuCard key={item.id} item={item} />
              ))}
            </div>
          ) : (
            <EmptyState
              icon={<PackageSearch size={24} />}
              title="No products match your filters"
              description="Try a different category or clear your search to see the full catalog."
              action={
                <button className="btn-soft" onClick={() => { setQ(""); setCategory(""); }}>
                  Clear filters
                </button>
              }
            />
          )}
        </>
      )}
    </div>
  );
}
