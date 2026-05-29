import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { menuApi } from "../lib/api/endpoints";
import { formatPrice, imageSrc, ALLERGEN_LABELS } from "../lib/format";
import { DietaryBadge } from "../components/menu/DietaryBadge";
import { useCartMutations } from "../hooks/useCart";
import { useAuth } from "../context/AuthProvider";
import { useToast } from "../context/ToastProvider";

export default function ItemDetail() {
  const { slug } = useParams();
  const nav = useNavigate();
  const toast = useToast();
  const { user } = useAuth();
  const { add } = useCartMutations();
  const { data: item, isLoading } = useQuery({
    queryKey: ["menu-item", slug],
    queryFn: () => menuApi.get(slug!),
    enabled: !!slug,
  });
  const [selected, setSelected] = useState<Record<string, string>>({});

  if (isLoading) return <div className="p-8 text-center text-gray-500">Loading…</div>;
  if (!item) return <div className="p-8 text-center">Item not found.</div>;

  const choose = (groupId: string, choiceId: string) =>
    setSelected((s) => ({ ...s, [groupId]: choiceId }));

  const extraCents = item.option_groups.reduce((sum, g) => {
    const cid = selected[g.id];
    const c = g.choices.find((x) => x.id === cid);
    return sum + (c?.price_delta_cents ?? 0);
  }, 0);

  const onAdd = () => {
    if (!user) return toast("Please log in to add items.", "info");
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
      <button className="mb-4 text-sm text-gray-500" onClick={() => nav(-1)}>← Back</button>
      <div className="card overflow-hidden">
        <img src={imageSrc(item.image_url)} alt={item.name} className="h-56 w-full object-cover" />
        <div className="p-6">
          <div className="flex items-start justify-between">
            <h1 className="text-2xl font-bold">{item.name}</h1>
            <span className="text-xl font-semibold text-brand-700">{formatPrice(item.price_cents + extraCents)}</span>
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

          <button className="btn-primary mt-6 w-full" onClick={onAdd} disabled={add.isPending}>
            Add to cart · {formatPrice(item.price_cents + extraCents)}
          </button>
        </div>
      </div>
    </div>
  );
}
