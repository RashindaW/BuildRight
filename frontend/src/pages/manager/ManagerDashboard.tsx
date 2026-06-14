import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { analyticsApi } from "../../lib/api/endpoints";
import { formatPrice } from "../../lib/format";

function Kpi({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="card p-4">
      <div className="text-xs uppercase tracking-wide text-gray-500">{label}</div>
      <div className="mt-1 text-2xl font-bold text-gray-900">{value}</div>
      {sub && <div className="mt-0.5 text-xs text-gray-500">{sub}</div>}
    </div>
  );
}

export default function ManagerDashboard() {
  const [days, setDays] = useState(30);
  const inv = useQuery({ queryKey: ["inventory"], queryFn: analyticsApi.inventory });
  const margins = useQuery({ queryKey: ["margins", days], queryFn: () => analyticsApi.margins(days) });
  const attr = useQuery({ queryKey: ["attr", days], queryFn: () => analyticsApi.aiAttribution(days) });
  const ops = useQuery({ queryKey: ["aiOps", days], queryFn: () => analyticsApi.aiOps(days) });

  const m = margins.data?.overall;
  const o = ops.data;
  const usd = (v: number) => `$${(v ?? 0).toFixed(v < 1 ? 4 : 2)}`;
  const maxRoute = Math.max(1, ...(o?.route_distribution ?? []).map((r) => r.count));
  const maxTool = Math.max(1, ...(o?.tool_usage ?? []).map((t) => t.count));

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">Manager Dashboard</h1>
        <label className="text-sm text-gray-600">
          Period:{" "}
          <select
            className="rounded-lg border border-gray-300 px-2 py-1"
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
            <option value={365}>Last year</option>
          </select>
        </label>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Kpi label="Revenue" value={formatPrice(m?.revenue_cents ?? 0)} sub={`${margins.data?.order_count ?? 0} orders`} />
        <Kpi label="Gross profit" value={formatPrice(m?.gross_profit_cents ?? 0)} sub={`${m?.margin_pct ?? 0}% margin`} />
        <Kpi
          label="AI-attributed revenue"
          value={formatPrice(attr.data?.chat_revenue_cents ?? 0)}
          sub={`${attr.data?.revenue_share_pct ?? 0}% of sales · ${attr.data?.chat_orders ?? 0} orders`}
        />
        <Kpi
          label="Low stock items"
          value={String(inv.data?.low_stock_count ?? 0)}
          sub={`${inv.data?.out_of_stock ?? 0} out of stock`}
        />
      </div>

      {/* Inventory */}
      <section className="mt-8">
        <h2 className="mb-3 text-lg font-semibold">Inventory</h2>
        <div className="grid gap-4 md:grid-cols-3">
          <Kpi label="Products" value={String(inv.data?.total_products ?? 0)} sub={`${inv.data?.in_stock ?? 0} in stock`} />
          <Kpi label="Inventory value (cost)" value={formatPrice(inv.data?.inventory_value_cost_cents ?? 0)} />
          <Kpi label="Inventory value (retail)" value={formatPrice(inv.data?.inventory_value_retail_cents ?? 0)} />
        </div>
        <div className="card mt-4 overflow-hidden">
          <div className="border-b bg-gray-50 px-4 py-2 text-sm font-medium">
            Low stock (≤ {inv.data?.low_stock_threshold ?? 15} units)
          </div>
          <table className="w-full text-sm">
            <thead className="text-left text-gray-500">
              <tr><th className="px-4 py-2">SKU</th><th className="px-4 py-2">Product</th><th className="px-4 py-2">Category</th><th className="px-4 py-2 text-right">Stock</th></tr>
            </thead>
            <tbody className="divide-y">
              {(inv.data?.low_stock ?? []).slice(0, 12).map((r) => (
                <tr key={r.sku ?? r.name}>
                  <td className="px-4 py-2 font-mono text-xs text-gray-500">{r.sku}</td>
                  <td className="px-4 py-2">{r.name}</td>
                  <td className="px-4 py-2 text-gray-500">{r.category}</td>
                  <td className="px-4 py-2 text-right font-medium text-amber-700">{r.stock_qty}</td>
                </tr>
              ))}
              {(inv.data?.low_stock?.length ?? 0) === 0 && (
                <tr><td colSpan={4} className="px-4 py-3 text-gray-400">No low-stock items.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* Profit by category */}
      <section className="mt-8">
        <h2 className="mb-3 text-lg font-semibold">Profit by category</h2>
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="text-left text-gray-500">
              <tr>
                <th className="px-4 py-2">Category</th>
                <th className="px-4 py-2 text-right">Revenue</th>
                <th className="px-4 py-2 text-right">COGS</th>
                <th className="px-4 py-2 text-right">Gross profit</th>
                <th className="px-4 py-2 text-right">Margin</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {(margins.data?.by_category ?? []).map((r) => (
                <tr key={r.category}>
                  <td className="px-4 py-2">{r.category}</td>
                  <td className="px-4 py-2 text-right">{formatPrice(r.revenue_cents)}</td>
                  <td className="px-4 py-2 text-right text-gray-500">{formatPrice(r.cogs_cents)}</td>
                  <td className="px-4 py-2 text-right font-medium text-green-700">{formatPrice(r.gross_profit_cents)}</td>
                  <td className="px-4 py-2 text-right">{r.margin_pct}%</td>
                </tr>
              ))}
              {(margins.data?.by_category?.length ?? 0) === 0 && (
                <tr><td colSpan={5} className="px-4 py-3 text-gray-400">No sales in this period.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* AI-attributed sales */}
      <section className="mt-8">
        <h2 className="mb-1 text-lg font-semibold">Where the AI assistant drove sales</h2>
        <p className="mb-3 text-sm text-gray-500">
          Orders whose items were added to the cart through the chat assistant.
          {attr.data && (
            <> {attr.data.chat_orders} of {attr.data.total_orders} orders ({attr.data.order_share_pct}%) ·
            {" "}{formatPrice(attr.data.chat_revenue_cents)} of {formatPrice(attr.data.total_revenue_cents)} revenue.</>
          )}
        </p>
        <div className="card overflow-hidden">
          <div className="border-b bg-gray-50 px-4 py-2 text-sm font-medium">Top chat-driven products</div>
          <table className="w-full text-sm">
            <thead className="text-left text-gray-500">
              <tr><th className="px-4 py-2">Product</th><th className="px-4 py-2 text-right">Units</th><th className="px-4 py-2 text-right">Revenue</th></tr>
            </thead>
            <tbody className="divide-y">
              {(attr.data?.top_chat_products ?? []).map((r) => (
                <tr key={r.name}>
                  <td className="px-4 py-2">{r.name}</td>
                  <td className="px-4 py-2 text-right">{r.units}</td>
                  <td className="px-4 py-2 text-right font-medium">{formatPrice(r.revenue_cents)}</td>
                </tr>
              ))}
              {(attr.data?.top_chat_products?.length ?? 0) === 0 && (
                <tr><td colSpan={3} className="px-4 py-3 text-gray-400">No chat-attributed sales yet — try reordering via the chat assistant.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* AI Operations — agent cost, thinking pattern, full visibility */}
      <section className="mt-8">
        <h2 className="mb-1 text-lg font-semibold">AI Operations</h2>
        <p className="mb-3 text-sm text-gray-500">
          What the assistant costs, how it routes &amp; reasons, and whether it stays grounded.
          {o && <> {o.turns} turns in the last {o.period_days} days.</>}
        </p>

        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <Kpi label="Agent cost" value={usd(o?.total_cost_usd ?? 0)} sub={`${o?.turns ?? 0} turns`} />
          <Kpi label="Avg cost / turn" value={usd(o?.avg_cost_usd ?? 0)} sub={`${o?.avg_tool_calls ?? 0} tool calls/turn`} />
          <Kpi label="Sonnet escalation" value={`${o?.escalation_rate_pct ?? 0}%`} sub="routed to the heavy model" />
          <Kpi
            label="Guardrail blocks"
            value={`${o?.guardrail_rate_pct ?? 0}%`}
            sub={`${o?.guardrail_violations ?? 0} blocked · quality ${o?.quality?.overall ?? "—"}`}
          />
        </div>

        <div className="mt-4 grid gap-4 md:grid-cols-3">
          {/* Cost by model */}
          <div className="card overflow-hidden">
            <div className="border-b bg-gray-50 px-4 py-2 text-sm font-medium">Cost by model</div>
            <table className="w-full text-sm">
              <tbody className="divide-y">
                {(o?.by_model ?? []).map((r) => (
                  <tr key={r.model}>
                    <td className="px-4 py-2">{r.model}</td>
                    <td className="px-4 py-2 text-right text-gray-500">{r.turns} turns</td>
                    <td className="px-4 py-2 text-right font-medium">{usd(r.cost_usd)}</td>
                  </tr>
                ))}
                {(o?.by_model?.length ?? 0) === 0 && (
                  <tr><td className="px-4 py-3 text-gray-400">No AI turns yet.</td></tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Route distribution (thinking pattern) */}
          <div className="card p-4">
            <div className="mb-2 text-sm font-medium">Route mix (thinking pattern)</div>
            <div className="space-y-2">
              {(o?.route_distribution ?? []).map((r) => (
                <div key={r.route}>
                  <div className="flex justify-between text-xs text-gray-600">
                    <span className="capitalize">{r.route}</span><span>{r.count} · {r.pct}%</span>
                  </div>
                  <div className="mt-0.5 h-2 rounded bg-gray-100">
                    <div className="h-2 rounded bg-brand-500" style={{ width: `${(r.count / maxRoute) * 100}%` }} />
                  </div>
                </div>
              ))}
              {(o?.route_distribution?.length ?? 0) === 0 && <div className="text-sm text-gray-400">No data.</div>}
            </div>
          </div>

          {/* Tool usage */}
          <div className="card p-4">
            <div className="mb-2 text-sm font-medium">Tool usage</div>
            <div className="space-y-2">
              {(o?.tool_usage ?? []).slice(0, 8).map((t) => (
                <div key={t.tool}>
                  <div className="flex justify-between text-xs text-gray-600">
                    <span className="font-mono">{t.tool}</span><span>{t.count}</span>
                  </div>
                  <div className="mt-0.5 h-2 rounded bg-gray-100">
                    <div className="h-2 rounded bg-green-500" style={{ width: `${(t.count / maxTool) * 100}%` }} />
                  </div>
                </div>
              ))}
              {(o?.tool_usage?.length ?? 0) === 0 && <div className="text-sm text-gray-400">No tool calls yet.</div>}
            </div>
          </div>
        </div>

        {/* Recent turns — full visibility */}
        <div className="card mt-4 overflow-x-auto">
          <div className="border-b bg-gray-50 px-4 py-2 text-sm font-medium">Recent turns</div>
          <table className="w-full text-sm">
            <thead className="text-left text-gray-500">
              <tr>
                <th className="px-4 py-2">When</th>
                <th className="px-4 py-2">Route</th>
                <th className="px-4 py-2">Model</th>
                <th className="px-4 py-2">Tools</th>
                <th className="px-4 py-2 text-right">Tokens</th>
                <th className="px-4 py-2 text-right">Cost</th>
                <th className="px-4 py-2 text-center">Guard</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {(o?.recent ?? []).map((r, i) => (
                <tr key={i}>
                  <td className="px-4 py-2 text-gray-500">{new Date(r.created_at).toLocaleString()}</td>
                  <td className="px-4 py-2 capitalize">{r.route ?? "—"}</td>
                  <td className="px-4 py-2 text-xs">{r.model ?? "—"}</td>
                  <td className="px-4 py-2 font-mono text-xs text-gray-600">{r.tools_used.join(", ") || "—"}</td>
                  <td className="px-4 py-2 text-right text-gray-500">{r.input_tokens + r.output_tokens}</td>
                  <td className="px-4 py-2 text-right font-medium">{usd(r.cost_usd)}</td>
                  <td className="px-4 py-2 text-center">{r.guardrail_violation ? "🛑" : "✓"}</td>
                </tr>
              ))}
              {(o?.recent?.length ?? 0) === 0 && (
                <tr><td colSpan={7} className="px-4 py-3 text-gray-400">No AI turns yet — chat with the assistant to populate this.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
