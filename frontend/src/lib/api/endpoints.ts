import { api, postForm } from "./client";
import type { Cart, Category, MenuItem, Order, Page, User } from "../../types";

// ---- Media (voice / image) ----
export const mediaApi = {
  transcribe: (audio: Blob, filename = "voice.webm") => {
    const form = new FormData();
    form.append("file", audio, filename);
    return postForm<{ text: string }>("/media/transcribe", form);
  },
};

// ---- Auth ----
export const authApi = {
  register: (email: string, password: string, full_name = "") =>
    api<User>("/auth/register", { method: "POST", body: { email, password, full_name } }),
  login: (email: string, password: string) =>
    api<User>("/auth/login", { method: "POST", body: { email, password } }),
  logout: () => api<{ message: string }>("/auth/logout", { method: "POST" }),
  me: () => api<User>("/auth/me"),
};

// ---- Menu ----
export interface MenuFilters {
  q?: string;
  category?: string;
  dietary?: string[];
  exclude_allergen?: string[];
}

export const menuApi = {
  list: (f: MenuFilters = {}) => {
    const p = new URLSearchParams();
    if (f.q) p.set("q", f.q);
    if (f.category) p.set("category", f.category);
    (f.dietary ?? []).forEach((d) => p.append("dietary", d));
    (f.exclude_allergen ?? []).forEach((a) => p.append("exclude_allergen", a));
    p.set("page_size", "100");
    return api<Page<MenuItem>>(`/menu?${p.toString()}`);
  },
  get: (slug: string) => api<MenuItem>(`/menu/${slug}`),
  categories: () => api<Category[]>("/menu/categories"),
  byIds: (ids: string[]) => api<MenuItem[]>("/menu/by-ids", { method: "POST", body: { ids } }),
};

// ---- Cart ----
export const cartApi = {
  get: () => api<Cart>("/cart"),
  add: (menu_item_id: string, quantity = 1, option_choice_ids: string[] = []) =>
    api<Cart>("/cart/items", { method: "POST", body: { menu_item_id, quantity, option_choice_ids } }),
  update: (cartItemId: string, quantity: number) =>
    api<Cart>(`/cart/items/${cartItemId}?quantity=${quantity}`, { method: "PATCH" }),
  remove: (cartItemId: string) => api<Cart>(`/cart/items/${cartItemId}`, { method: "DELETE" }),
  clear: () => api<{ message: string }>("/cart", { method: "DELETE" }),
};

// ---- Orders ----
export const ordersApi = {
  create: (notes?: string, guestEmail?: string) =>
    api<Order>("/orders", { method: "POST", body: { notes: notes ?? null, guest_email: guestEmail ?? null } }),
  list: () => api<Order[]>("/orders"),
  get: (id: string) => api<Order>(`/orders/${id}`),
};

// ---- Payments ----
export interface CreateIntentResponse {
  client_secret: string;
  order_id: string;
  publishable_key: string;
}

export interface PaymentStatusResponse {
  payment_status: string;
  order_status: string;
  order_id: string;
}

export const paymentsApi = {
  createIntent: (notes?: string, guestEmail?: string) =>
    api<CreateIntentResponse>("/payments/create-intent", {
      method: "POST",
      body: { notes: notes ?? null, guest_email: guestEmail ?? null },
    }),
  confirm: (orderId: string) =>
    api<{ payment_status: string; order_status: string; pi_status: string }>(
      `/payments/confirm/${orderId}`,
      { method: "POST" }
    ),
  status: (orderId: string) =>
    api<PaymentStatusResponse>(`/payments/status/${orderId}`),
};

// ---- Manager analytics ----
export interface InventorySummary {
  total_products: number;
  in_stock: number;
  out_of_stock: number;
  low_stock_count: number;
  low_stock_threshold: number;
  inventory_value_cost_cents: number;
  inventory_value_retail_cents: number;
  low_stock: { sku: string | null; name: string; category: string; stock_qty: number }[];
  by_category: { category: string; products: number; units: number }[];
}

export interface MarginRow {
  revenue_cents: number;
  cogs_cents: number;
  gross_profit_cents: number;
  margin_pct: number;
}

export interface MarginSummary {
  period_days: number;
  order_count: number;
  overall: MarginRow;
  by_category: ({ category: string } & MarginRow)[];
}

export interface AiAttribution {
  period_days: number;
  total_orders: number;
  total_revenue_cents: number;
  chat_orders: number;
  chat_revenue_cents: number;
  order_share_pct: number;
  revenue_share_pct: number;
  top_chat_products: { name: string; units: number; revenue_cents: number }[];
}

export const analyticsApi = {
  inventory: () => api<InventorySummary>("/analytics/inventory"),
  margins: (days = 30) => api<MarginSummary>(`/analytics/margins?days=${days}`),
  aiAttribution: (days = 30) => api<AiAttribution>(`/analytics/ai-attribution?days=${days}`),
};

// ---- Admin ----
export const adminApi = {
  createItem: (body: Record<string, unknown>) =>
    api<MenuItem>("/admin/menu", { method: "POST", body }),
  updateItem: (id: string, body: Record<string, unknown>) =>
    api<MenuItem>(`/admin/menu/${id}`, { method: "PATCH", body }),
  deleteItem: (id: string) => api<{ message: string }>(`/admin/menu/${id}`, { method: "DELETE" }),
  orders: () => api<Order[]>("/admin/orders"),
  setOrderStatus: (id: string, status: string) =>
    api<Order>(`/admin/orders/${id}/status`, { method: "PATCH", body: { status } }),
  users: () => api<User[]>("/admin/users"),
};
