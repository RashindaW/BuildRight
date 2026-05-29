import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi, menuApi, ordersApi } from "../../lib/api/endpoints";
import { formatPrice } from "../../lib/format";
import { useToast } from "../../context/ToastProvider";
import type { Order } from "../../types";

const ORDER_STATUSES = ["placed", "preparing", "ready", "completed", "cancelled"];

export default function AdminDashboard() {
  const [tab, setTab] = useState<"orders" | "menu">("orders");
  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <h1 className="mb-6 text-2xl font-bold">Admin Dashboard</h1>
      <div className="mb-4 flex gap-2">
        <button className={tab === "orders" ? "btn-primary" : "btn-ghost"} onClick={() => setTab("orders")}>Orders</button>
        <button className={tab === "menu" ? "btn-primary" : "btn-ghost"} onClick={() => setTab("menu")}>Menu</button>
      </div>
      {tab === "orders" ? <OrdersPanel /> : <MenuPanel />}
    </div>
  );
}

function OrdersPanel() {
  const qc = useQueryClient();
  const toast = useToast();
  const { data: orders } = useQuery({ queryKey: ["admin-orders"], queryFn: adminApi.orders });
  const setStatus = useMutation({
    mutationFn: (v: { id: string; status: string }) => adminApi.setOrderStatus(v.id, v.status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-orders"] });
      toast("Order updated", "success");
    },
    onError: (e) => toast((e as Error).message, "error"),
  });

  return (
    <div className="space-y-3">
      {(orders ?? []).map((o: Order) => (
        <div key={o.id} className="card flex items-center justify-between p-4">
          <div>
            <span className="font-mono font-semibold">{o.order_number}</span>
            <p className="text-sm text-gray-500">{o.items.length} items · {formatPrice(o.total_cents)}</p>
          </div>
          <select
            className="rounded-lg border border-gray-300 px-2 py-1"
            value={o.status}
            onChange={(e) => setStatus.mutate({ id: o.id, status: e.target.value })}
          >
            {ORDER_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
      ))}
      {orders && orders.length === 0 && <p className="text-gray-500">No orders yet.</p>}
    </div>
  );
}

function MenuPanel() {
  const qc = useQueryClient();
  const toast = useToast();
  const { data: menu } = useQuery({ queryKey: ["admin-menu"], queryFn: () => menuApi.list() });
  const del = useMutation({
    mutationFn: (id: string) => adminApi.deleteItem(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-menu"] });
      qc.invalidateQueries({ queryKey: ["menu"] });
      toast("Item deleted", "success");
    },
    onError: (e) => toast((e as Error).message, "error"),
  });

  return (
    <div className="card divide-y">
      {(menu?.items ?? []).map((m) => (
        <div key={m.id} className="flex items-center justify-between p-3">
          <span>{m.name} <span className="text-gray-400">({m.category})</span></span>
          <div className="flex items-center gap-3">
            <span className="font-semibold">{formatPrice(m.price_cents)}</span>
            <button className="text-sm text-red-600" onClick={() => del.mutate(m.id)}>Delete</button>
          </div>
        </div>
      ))}
    </div>
  );
}
