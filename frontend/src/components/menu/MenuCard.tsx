import { Link } from "react-router-dom";
import type { MenuItem } from "../../types";
import { formatPrice, imageSrc } from "../../lib/format";
import { DietaryBadge } from "./DietaryBadge";
import { useCartMutations } from "../../hooks/useCart";
import { useAuth } from "../../context/AuthProvider";
import { useToast } from "../../context/ToastProvider";

export function MenuCard({ item }: { item: MenuItem }) {
  const { add } = useCartMutations();
  const { user } = useAuth();
  const toast = useToast();
  const hasOptions = item.option_groups.length > 0;

  const onAdd = () => {
    if (!user) return toast("Please log in to add items.", "info");
    add.mutate(
      { id: item.slug },
      {
        onSuccess: () => toast(`${item.name} added to cart`, "success"),
        onError: (e) => toast((e as Error).message, "error"),
      },
    );
  };

  return (
    <div className="card flex flex-col overflow-hidden">
      <Link to={`/item/${item.slug}`}>
        <img
          src={imageSrc(item.image_url)}
          alt={item.name}
          className="h-40 w-full object-cover"
          loading="lazy"
        />
      </Link>
      <div className="flex flex-1 flex-col p-4">
        <div className="flex items-start justify-between gap-2">
          <Link to={`/item/${item.slug}`} className="font-semibold hover:text-brand-600">
            {item.name}
          </Link>
          <span className="whitespace-nowrap font-semibold text-brand-700">
            {formatPrice(item.price_cents)}
          </span>
        </div>
        <p className="mt-1 line-clamp-2 text-sm text-gray-600">{item.description}</p>
        <div className="mt-2 flex flex-wrap gap-1">
          {item.dietary_tags.map((t) => (
            <DietaryBadge key={t} tag={t} />
          ))}
        </div>
        <div className="mt-auto pt-3">
          {hasOptions ? (
            <Link to={`/item/${item.slug}`} className="btn-ghost w-full">
              Choose options
            </Link>
          ) : (
            <button className="btn-primary w-full" onClick={onAdd} disabled={add.isPending}>
              Add to cart
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
