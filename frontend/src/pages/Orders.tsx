import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ordersApi } from "../lib/api/endpoints";
import { formatPrice } from "../lib/format";

const STATUS_COLOR: Record<string, string> = {
  placed: "bg-blue-100 text-blue-800",
  preparing: "bg-amber-100 text-amber-800",
  ready: "bg-green-100 text-green-800",
  completed: "bg-gray-100 text-gray-700",
  cancelled: "bg-red-100 text-red-800",
};

export default function Orders() {
  const { data: orders, isLoading } = useQuery({ queryKey: ["orders"], queryFn: ordersApi.list });

  if (isLoading) return <div className="p-8 text-center text-gray-500">Loading…</div>;

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="mb-6 text-2xl font-bold">My Orders</h1>
      {!orders || orders.length === 0 ? (
        <p className="text-gray-500">You have no orders yet.</p>
      ) : (
        <ul className="space-y-3">
          {orders.map((o) => (
            <li key={o.id} className="card flex items-center justify-between p-4">
              <div>
                <Link to={`/order/${o.id}`} className="font-mono font-semibold hover:text-brand-600">
                  {o.order_number}
                </Link>
                <p className="text-sm text-gray-500">
                  {new Date(o.created_at).toLocaleString()} · {o.items.length} item(s)
                </p>
              </div>
              <div className="text-right">
                <span className={`rounded-full px-2 py-0.5 text-xs ${STATUS_COLOR[o.status] ?? ""}`}>{o.status}</span>
                <p className="mt-1 font-semibold">{formatPrice(o.total_cents)}</p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
