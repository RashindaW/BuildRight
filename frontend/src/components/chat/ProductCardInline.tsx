import { Link } from "react-router-dom";
import { Plus } from "lucide-react";
import type { MenuItem } from "../../types";
import { formatPrice, imageSrc } from "../../lib/format";
import { useCartMutations } from "../../hooks/useCart";
import { useUiStore } from "../../store/uiStore";
import { useToast } from "../../context/ToastProvider";
import { Stars } from "../ui/Stars";

const PLACEHOLDER = "/img/_placeholder.svg";

/** Compact, interactive product card rendered inline in an assistant chat message. */
export function ProductCardInline({ item, onNavigate }: { item: MenuItem; onNavigate?: () => void }) {
  const { add } = useCartMutations();
  const setCartOpen = useUiStore((s) => s.setCartOpen);
  const toast = useToast();
  const outOfStock = !item.is_available || item.stock_qty <= 0;

  const onAdd = () =>
    add.mutate(
      { id: item.slug },
      {
        onSuccess: () => {
          toast(`${item.name} added to cart`, "success");
          setCartOpen(true);
        },
        onError: (e) => toast((e as Error).message, "error"),
      },
    );

  return (
    <div className="flex animate-fade-in-up gap-3 rounded-xl border border-gray-200 bg-white p-2.5 text-left shadow-card">
      <Link to={`/item/${item.slug}`} onClick={onNavigate} className="shrink-0">
        <img
          src={imageSrc(item.image_url)}
          alt={item.name}
          className="h-16 w-16 rounded-lg object-cover"
          loading="lazy"
          onError={(e) => {
            e.currentTarget.onerror = null;
            e.currentTarget.src = PLACEHOLDER;
          }}
        />
      </Link>
      <div className="min-w-0 flex-1">
        <Link
          to={`/item/${item.slug}`}
          onClick={onNavigate}
          className="block truncate text-sm font-semibold text-gray-900 hover:text-brand-600"
        >
          {item.name}
        </Link>
        <div className="mt-0.5 flex items-center gap-2">
          <span className="text-sm font-semibold text-brand-700">{formatPrice(item.price_cents)}</span>
          {(item.rating_count ?? 0) > 0 && <Stars value={item.rating_avg ?? 0} size={11} />}
        </div>
        <div className="mt-1.5 flex items-center gap-2">
          <button className="btn-primary btn-sm" onClick={onAdd} disabled={add.isPending || outOfStock}>
            <Plus size={13} /> {outOfStock ? "Out of stock" : "Add"}
          </button>
          <Link to={`/item/${item.slug}`} onClick={onNavigate} className="btn-ghost btn-sm">
            View
          </Link>
        </div>
      </div>
    </div>
  );
}
