import { Link } from "react-router-dom";
import { Plus } from "lucide-react";
import type { MenuItem } from "../../types";
import { formatPrice, imageSrc } from "../../lib/format";
import { useCartMutations } from "../../hooks/useCart";
import { useToast } from "../../context/ToastProvider";
import { Stars } from "../ui/Stars";

const PLACEHOLDER = "/img/_placeholder.svg";

export function MenuCard({ item }: { item: MenuItem }) {
  const { add } = useCartMutations();
  const toast = useToast();
  const hasOptions = item.option_groups.length > 0;
  const outOfStock = !item.is_available || item.stock_qty <= 0;
  const lowStock = !outOfStock && item.stock_qty <= 15;
  const onSale = item.dietary_tags.includes("sale");
  const isNew = item.dietary_tags.includes("new-arrival");

  const onAdd = () => {
    add.mutate(
      { id: item.slug },
      {
        onSuccess: () => toast(`${item.name} added to cart`, "success"),
        onError: (e) => toast((e as Error).message, "error"),
      },
    );
  };

  return (
    <div className="card card-hover group flex flex-col overflow-hidden">
      <Link to={`/item/${item.slug}`} className="relative block overflow-hidden bg-gray-100">
        <img
          src={imageSrc(item.image_url)}
          alt={item.name}
          className="aspect-[4/3] w-full object-cover transition-transform duration-300 group-hover:scale-105"
          loading="lazy"
          onError={(e) => {
            e.currentTarget.onerror = null;
            e.currentTarget.src = PLACEHOLDER;
          }}
        />
        {(onSale || isNew) && (
          <div className="absolute left-2 top-2 flex gap-1">
            {onSale && <span className="badge-brand shadow-sm">Sale</span>}
            {isNew && <span className="badge bg-success text-white shadow-sm">New</span>}
          </div>
        )}
        {outOfStock && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/70 backdrop-blur-[1px]">
            <span className="badge bg-gray-800 text-white">Out of stock</span>
          </div>
        )}
      </Link>
      <div className="flex flex-1 flex-col p-4">
        <div className="flex items-start justify-between gap-2">
          <Link to={`/item/${item.slug}`} className="font-semibold leading-snug hover:text-brand-600">
            {item.name}
          </Link>
          <span className="whitespace-nowrap font-semibold text-brand-700">
            {formatPrice(item.price_cents)}
          </span>
        </div>
        {(item.rating_count ?? 0) > 0 && (
          <div className="mt-1">
            <Stars value={item.rating_avg ?? 0} count={item.rating_count} />
          </div>
        )}
        <div className="mt-1 flex items-center gap-2">
          {item.sku && <span className="font-mono text-xs text-gray-400">SKU {item.sku}</span>}
          {!outOfStock && lowStock ? (
            <span className="badge-warning">Only {item.stock_qty} left</span>
          ) : !outOfStock ? (
            <span className="badge-success">In stock</span>
          ) : null}
        </div>
        <p className="mt-1 line-clamp-2 text-sm text-gray-600">{item.description}</p>
        <div className="mt-auto pt-3">
          {hasOptions ? (
            <Link to={`/item/${item.slug}`} className="btn-ghost w-full">
              Choose options
            </Link>
          ) : (
            <button
              className="btn-primary w-full"
              onClick={onAdd}
              disabled={add.isPending || outOfStock}
            >
              {!outOfStock && <Plus size={16} />}
              {outOfStock ? "Out of stock" : add.isPending ? "Adding…" : "Add to cart"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
