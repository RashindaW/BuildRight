import { Link } from "react-router-dom";
import { useCart, useCartMutations } from "../../hooks/useCart";
import { useUiStore } from "../../store/uiStore";
import { formatPrice } from "../../lib/format";

export function CartDrawer() {
  const { cartOpen, setCartOpen } = useUiStore();
  const { data: cart } = useCart();
  const { update, remove } = useCartMutations();

  if (!cartOpen) return null;

  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/30" onClick={() => setCartOpen(false)} />
      <aside className="absolute right-0 top-0 flex h-full w-96 max-w-full flex-col bg-white shadow-xl">
        <div className="flex items-center justify-between border-b p-4">
          <h2 className="text-lg font-semibold">Your Cart</h2>
          <button onClick={() => setCartOpen(false)} aria-label="Close cart">✕</button>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {!cart || cart.items.length === 0 ? (
            <p className="text-gray-500">Your cart is empty.</p>
          ) : (
            <ul className="space-y-3">
              {cart.items.map((it) => (
                <li key={it.id} className="card p-3">
                  <div className="flex justify-between">
                    <span className="font-medium">{it.name}</span>
                    <span>{formatPrice(it.line_total_cents)}</span>
                  </div>
                  {it.options.length > 0 && (
                    <p className="text-xs text-gray-500">{it.options.join(", ")}</p>
                  )}
                  <div className="mt-2 flex items-center gap-2">
                    <button className="btn-ghost px-2 py-0.5" onClick={() => update.mutate({ itemId: it.id, qty: it.quantity - 1 })}>
                      −
                    </button>
                    <span>{it.quantity}</span>
                    <button className="btn-ghost px-2 py-0.5" onClick={() => update.mutate({ itemId: it.id, qty: it.quantity + 1 })}>
                      +
                    </button>
                    <button className="ml-auto text-sm text-red-600" onClick={() => remove.mutate(it.id)}>
                      Remove
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="border-t p-4">
          <div className="mb-3 flex justify-between font-semibold">
            <span>Subtotal</span>
            <span>{formatPrice(cart?.subtotal_cents ?? 0)}</span>
          </div>
          <Link
            to="/checkout"
            className="btn-primary w-full"
            onClick={() => setCartOpen(false)}
            aria-disabled={!cart || cart.items.length === 0}
          >
            Checkout
          </Link>
        </div>
      </aside>
    </div>
  );
}
