import { Link } from "react-router-dom";
import { Minus, Plus, ShoppingCart, Trash2, X } from "lucide-react";
import { useCart, useCartMutations } from "../../hooks/useCart";
import { useUiStore } from "../../store/uiStore";
import { formatPrice } from "../../lib/format";
import { EmptyState } from "../ui/EmptyState";

export function CartDrawer() {
  const { cartOpen, setCartOpen } = useUiStore();
  const { data: cart } = useCart();
  const { update, remove } = useCartMutations();

  if (!cartOpen) return null;
  const empty = !cart || cart.items.length === 0;

  return (
    <div className="fixed inset-0 z-50">
      <div
        className="absolute inset-0 animate-fade-in bg-black/40 backdrop-blur-[1px]"
        onClick={() => setCartOpen(false)}
      />
      <aside className="absolute right-0 top-0 flex h-full w-96 max-w-full animate-slide-in-right flex-col bg-white shadow-pop">
        <div className="flex items-center justify-between border-b border-gray-100 p-4">
          <h2 className="flex items-center gap-2 text-lg font-semibold">
            <ShoppingCart size={18} className="text-brand-600" /> Your Cart
          </h2>
          <button
            onClick={() => setCartOpen(false)}
            aria-label="Close cart"
            className="grid h-8 w-8 place-items-center rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-900"
          >
            <X size={18} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {empty ? (
            <div className="pt-8">
              <EmptyState
                icon={<ShoppingCart size={24} />}
                title="Your cart is empty"
                description="Add products from the catalog or ask the assistant to build a list for you."
                action={
                  <button className="btn-soft" onClick={() => setCartOpen(false)}>
                    Browse products
                  </button>
                }
              />
            </div>
          ) : (
            <ul className="space-y-3">
              {cart!.items.map((it) => (
                <li key={it.id} className="card p-3">
                  <div className="flex justify-between gap-2">
                    <span className="font-medium leading-snug">{it.name}</span>
                    <span className="whitespace-nowrap font-semibold">
                      {formatPrice(it.line_total_cents)}
                    </span>
                  </div>
                  {it.options.length > 0 && (
                    <p className="mt-0.5 text-xs text-gray-500">{it.options.join(", ")}</p>
                  )}
                  <div className="mt-2 flex items-center gap-2">
                    <div className="inline-flex items-center rounded-lg border border-gray-200">
                      <button
                        className="grid h-7 w-7 place-items-center text-gray-600 hover:bg-gray-50 disabled:opacity-40"
                        onClick={() => update.mutate({ itemId: it.id, qty: it.quantity - 1 })}
                        disabled={it.quantity <= 1}
                        aria-label="Decrease quantity"
                      >
                        <Minus size={14} />
                      </button>
                      <span className="w-7 text-center text-sm font-medium">{it.quantity}</span>
                      <button
                        className="grid h-7 w-7 place-items-center text-gray-600 hover:bg-gray-50"
                        onClick={() => update.mutate({ itemId: it.id, qty: it.quantity + 1 })}
                        aria-label="Increase quantity"
                      >
                        <Plus size={14} />
                      </button>
                    </div>
                    <button
                      className="ml-auto inline-flex items-center gap-1 text-sm text-danger hover:text-danger-dark"
                      onClick={() => remove.mutate(it.id)}
                    >
                      <Trash2 size={14} /> Remove
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="border-t border-gray-100 p-4">
          <div className="mb-3 flex justify-between text-base font-semibold">
            <span>Subtotal</span>
            <span>{formatPrice(cart?.subtotal_cents ?? 0)}</span>
          </div>
          <Link
            to="/checkout"
            className={`btn-primary w-full ${empty ? "pointer-events-none opacity-50" : ""}`}
            onClick={() => setCartOpen(false)}
            aria-disabled={empty}
          >
            Checkout
          </Link>
        </div>
      </aside>
    </div>
  );
}
