import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useCart, useCartMutations } from "../hooks/useCart";
import { ordersApi } from "../lib/api/endpoints";
import { formatPrice } from "../lib/format";
import { useToast } from "../context/ToastProvider";
import { useQueryClient } from "@tanstack/react-query";

export default function Checkout() {
  const { data: cart } = useCart();
  const nav = useNavigate();
  const toast = useToast();
  const qc = useQueryClient();
  const [notes, setNotes] = useState("");
  const [placing, setPlacing] = useState(false);

  const placeOrder = async () => {
    setPlacing(true);
    try {
      const order = await ordersApi.create(notes || undefined);
      qc.invalidateQueries({ queryKey: ["cart"] });
      qc.invalidateQueries({ queryKey: ["orders"] });
      nav(`/order/${order.id}`);
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setPlacing(false);
    }
  };

  if (!cart || cart.items.length === 0) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-12 text-center">
        <p className="text-gray-500">Your cart is empty.</p>
        <button className="btn-primary mt-4" onClick={() => nav("/")}>Browse the menu</button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      <h1 className="mb-6 text-2xl font-bold">Checkout</h1>
      <div className="card p-4">
        <ul className="divide-y">
          {cart.items.map((it) => (
            <li key={it.id} className="flex justify-between py-2">
              <span>{it.quantity} × {it.name}</span>
              <span>{formatPrice(it.line_total_cents)}</span>
            </li>
          ))}
        </ul>
        <div className="mt-3 flex justify-between border-t pt-3 text-lg font-semibold">
          <span>Total</span>
          <span>{formatPrice(cart.subtotal_cents)}</span>
        </div>
      </div>

      <label className="mt-4 block text-sm font-medium">
        Order notes (optional)
        <textarea
          className="mt-1 w-full rounded-lg border border-gray-300 p-2"
          rows={3}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          maxLength={500}
        />
      </label>

      <button className="btn-primary mt-4 w-full" onClick={placeOrder} disabled={placing}>
        {placing ? "Placing order…" : `Place order · ${formatPrice(cart.subtotal_cents)}`}
      </button>
      <p className="mt-2 text-center text-xs text-gray-400">This is a demo — no payment is taken.</p>
    </div>
  );
}
