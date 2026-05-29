import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ordersApi } from "../lib/api/endpoints";
import { formatPrice } from "../lib/format";

export default function OrderConfirmation() {
  const { id } = useParams();
  const { data: order, isLoading } = useQuery({
    queryKey: ["order", id],
    queryFn: () => ordersApi.get(id!),
    enabled: !!id,
  });

  if (isLoading) return <div className="p-8 text-center text-gray-500">Loading…</div>;
  if (!order) return <div className="p-8 text-center">Order not found.</div>;

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      <div className="card p-6 text-center">
        <div className="text-5xl">✅</div>
        <h1 className="mt-2 text-2xl font-bold">Order placed!</h1>
        <p className="mt-1 text-gray-600">
          Order <span className="font-mono font-semibold">{order.order_number}</span> · status: {order.status}
        </p>
      </div>
      <div className="card mt-4 p-4">
        <ul className="divide-y">
          {order.items.map((it) => (
            <li key={it.id} className="flex justify-between py-2">
              <span>{it.quantity} × {it.name_snapshot}</span>
              <span>{formatPrice(it.line_total_cents)}</span>
            </li>
          ))}
        </ul>
        <div className="mt-3 flex justify-between border-t pt-3 font-semibold">
          <span>Total</span>
          <span>{formatPrice(order.total_cents)}</span>
        </div>
      </div>
      <div className="mt-4 flex gap-3">
        <Link to="/orders" className="btn-ghost flex-1">View my orders</Link>
        <Link to="/" className="btn-primary flex-1">Back to menu</Link>
      </div>
    </div>
  );
}
