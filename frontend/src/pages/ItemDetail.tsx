import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Plus } from "lucide-react";
import { menuApi } from "../lib/api/endpoints";
import { formatPrice, imageSrc, ALLERGEN_LABELS } from "../lib/format";
import { DietaryBadge } from "../components/menu/DietaryBadge";
import { MenuCard } from "../components/menu/MenuCard";
import { ProductReviews } from "../components/menu/ProductReviews";
import { Skeleton } from "../components/ui/Skeleton";
import { Stars } from "../components/ui/Stars";
import { useCartMutations } from "../hooks/useCart";
import { useToast } from "../context/ToastProvider";

export default function ItemDetail() {
  const { slug } = useParams();
  const nav = useNavigate();
  const toast = useToast();
  const { add } = useCartMutations();
  const { data: item, isLoading } = useQuery({
    queryKey: ["menu-item", slug],
    queryFn: () => menuApi.get(slug!),
    enabled: !!slug,
  });
  const recs = useQuery({
    queryKey: ["recommendations", slug],
    queryFn: () => menuApi.recommendations(slug!),
    enabled: !!slug,
  });
  const [selected, setSelected] = useState<Record<string, string>>({});

  if (isLoading)
    return (
      <div className="mx-auto max-w-3xl px-4 py-8">
        <div className="card overflow-hidden">
          <Skeleton className="h-56 w-full rounded-none" />
          <div className="space-y-3 p-6">
            <Skeleton className="h-7 w-2/3" />
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-11 w-full" />
          </div>
        </div>
      </div>
    );
  if (!item) return <div className="p-8 text-center">Item not found.</div>;

  const outOfStock = !item.is_available || item.stock_qty <= 0;

  const choose = (groupId: string, choiceId: string) =>
    setSelected((s) => ({ ...s, [groupId]: choiceId }));

  const extraCents = item.option_groups.reduce((sum, g) => {
    const cid = selected[g.id];
    const c = g.choices.find((x) => x.id === cid);
    return sum + (c?.price_delta_cents ?? 0);
  }, 0);

  const onAdd = () => {
    const missing = item.option_groups.filter((g) => g.required && !selected[g.id]);
    if (missing.length) return toast(`Please choose: ${missing.map((m) => m.name).join(", ")}`, "error");
    add.mutate(
      { id: item.slug, options: Object.values(selected) },
      {
        onSuccess: () => {
          toast(`${item.name} added`, "success");
          nav("/");
        },
        onError: (e) => toast((e as Error).message, "error"),
      },
    );
  };

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <button
        className="mb-4 inline-flex items-center gap-1 text-sm text-gray-500 transition-colors hover:text-gray-800"
        onClick={() => nav(-1)}
      >
        <ArrowLeft size={16} /> Back
      </button>
      <div className="card overflow-hidden">
        <img src={imageSrc(item.image_url)} alt={item.name} className="h-56 w-full object-cover" />
        <div className="p-6">
          <div className="flex items-start justify-between gap-3">
            <h1 className="text-2xl font-bold tracking-tight">{item.name}</h1>
            <span className="whitespace-nowrap text-xl font-semibold text-brand-700">{formatPrice(item.price_cents + extraCents)}</span>
          </div>
          {(item.rating_count ?? 0) > 0 && (
            <div className="mt-1.5">
              <Stars value={item.rating_avg ?? 0} count={item.rating_count} showValue size={16} />
            </div>
          )}
          <div className="mt-1.5 flex flex-wrap items-center gap-3">
            {item.sku && <span className="font-mono text-xs text-gray-400">SKU {item.sku}</span>}
            <span className="text-xs font-medium text-gray-500">{item.category}</span>
            {outOfStock ? (
              <span className="badge-neutral">Out of stock</span>
            ) : item.stock_qty <= 15 ? (
              <span className="badge-warning">Only {item.stock_qty} left in stock</span>
            ) : (
              <span className="badge-success">{item.stock_qty} in stock</span>
            )}
          </div>
          <p className="mt-2 text-gray-600">{item.description}</p>

          <div className="mt-3 flex flex-wrap gap-1">
            {item.dietary_tags.map((t) => <DietaryBadge key={t} tag={t} />)}
          </div>

          {item.allergens.length > 0 && (
            <p className="mt-3 text-sm text-red-700">
              <strong>Allergens:</strong> {item.allergens.map((a) => ALLERGEN_LABELS[a] ?? a).join(", ")}
            </p>
          )}
          {item.calories != null && (
            <p className="mt-1 text-sm text-gray-500">{item.calories} kcal{item.spice_level > 0 ? ` · spice ${item.spice_level}/3` : ""}</p>
          )}

          {item.option_groups.map((g) => (
            <fieldset key={g.id} className="mt-4">
              <legend className="font-medium">
                {g.name} {g.required && <span className="text-red-600">*</span>}
              </legend>
              <div className="mt-1 space-y-1">
                {g.choices.map((c) => (
                  <label key={c.id} className="flex items-center gap-2 text-sm">
                    <input
                      type="radio"
                      name={g.id}
                      checked={selected[g.id] === c.id}
                      onChange={() => choose(g.id, c.id)}
                    />
                    {c.name}
                    {c.price_delta_cents > 0 && <span className="text-gray-500">+{formatPrice(c.price_delta_cents)}</span>}
                  </label>
                ))}
              </div>
            </fieldset>
          ))}

          <button className="btn-primary mt-6 w-full" onClick={onAdd} disabled={add.isPending || outOfStock}>
            {!outOfStock && <Plus size={16} />}
            {outOfStock ? "Out of stock" : `Add to cart · ${formatPrice(item.price_cents + extraCents)}`}
          </button>
        </div>
      </div>

      {recs.data && recs.data.length > 0 && (
        <section className="mt-8">
          <h2 className="mb-3 text-lg font-semibold">You might also like</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {recs.data.map((it) => (
              <MenuCard key={it.id} item={it} />
            ))}
          </div>
        </section>
      )}

      <ProductReviews slug={item.slug} />
    </div>
  );
}
