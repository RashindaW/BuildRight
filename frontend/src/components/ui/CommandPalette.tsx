import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Bot, Compass, Info, Package, Search, ShoppingCart } from "lucide-react";
import { menuApi } from "../../lib/api/endpoints";
import { formatPrice } from "../../lib/format";
import { useUiStore } from "../../store/uiStore";

/** Ctrl/Cmd+K command palette: instant product search + quick actions. */
export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [sel, setSel] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const nav = useNavigate();
  const setChatOpen = useUiStore((s) => s.setChatOpen);
  const setCartOpen = useUiStore((s) => s.setCartOpen);

  // Global hotkey
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      } else if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (open) {
      setQ("");
      setSel(0);
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  const [debounced, setDebounced] = useState("");
  useEffect(() => {
    const t = setTimeout(() => setDebounced(q), 180);
    return () => clearTimeout(t);
  }, [q]);

  const results = useQuery({
    queryKey: ["palette", debounced],
    queryFn: () => menuApi.list({ q: debounced }),
    enabled: open && debounced.length > 1,
  });

  const products = (results.data?.items ?? []).slice(0, 6);

  const actions = useMemo(
    () => [
      { icon: Bot, label: "Ask the assistant", run: () => setChatOpen(true) },
      { icon: Compass, label: "Take the tour", run: () => nav("/how-to-test") },
      { icon: Info, label: "How it's built", run: () => nav("/about") },
      { icon: ShoppingCart, label: "Open cart", run: () => setCartOpen(true) },
    ],
    [nav, setCartOpen, setChatOpen],
  );

  const rows = useMemo(
    () => [
      ...products.map((p) => ({
        key: `p-${p.id}`,
        icon: Package,
        label: p.name,
        hint: formatPrice(p.price_cents),
        run: () => nav(`/item/${p.slug}`),
      })),
      ...(q.length <= 1 ? actions.map((a, i) => ({ key: `a-${i}`, hint: "", ...a })) : []),
    ],
    [products, actions, q, nav],
  );

  const pick = useCallback(
    (i: number) => {
      const row = rows[i];
      if (!row) return;
      setOpen(false);
      row.run();
    },
    [rows],
  );

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-brand-900/40 p-4 pt-[12vh] backdrop-blur-sm animate-fade-in"
      onClick={() => setOpen(false)}
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
    >
      <div
        className="w-full max-w-lg overflow-hidden rounded-xl2 border border-gray-200 bg-white shadow-pop animate-fade-in-up"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2 border-b px-4 py-3">
          <Search size={16} className="shrink-0 text-gray-400" />
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setSel(0);
            }}
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") {
                e.preventDefault();
                setSel((s) => Math.min(rows.length - 1, s + 1));
              } else if (e.key === "ArrowUp") {
                e.preventDefault();
                setSel((s) => Math.max(0, s - 1));
              } else if (e.key === "Enter") {
                e.preventDefault();
                pick(sel);
              }
            }}
            placeholder="Search products or jump to…"
            className="w-full bg-transparent text-sm outline-none placeholder:text-gray-400"
            aria-label="Search products or actions"
          />
          <kbd className="rounded border border-gray-200 bg-gray-50 px-1.5 py-0.5 text-[10px] text-gray-400">esc</kbd>
        </div>
        <ul className="max-h-80 overflow-y-auto p-2">
          {rows.length === 0 && (
            <li className="px-3 py-6 text-center text-sm text-gray-400">
              {q.length > 1 ? "No matches — try a different term." : "Type to search the catalog…"}
            </li>
          )}
          {rows.map((r, i) => {
            const Icon = r.icon;
            return (
              <li key={r.key}>
                <button
                  className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm ${
                    i === sel ? "bg-brand-50 text-brand-800" : "text-gray-700 hover:bg-gray-50"
                  }`}
                  onMouseEnter={() => setSel(i)}
                  onClick={() => pick(i)}
                >
                  <Icon size={15} className="shrink-0 text-gray-400" />
                  <span className="min-w-0 flex-1 truncate">{r.label}</span>
                  {r.hint && <span className="shrink-0 text-xs text-gray-400">{r.hint}</span>}
                </button>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
