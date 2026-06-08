import { api } from "./client";
import type { Cart, Category, MenuItem, Order, Page, User } from "../../types";

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
  create: (notes?: string) => api<Order>("/orders", { method: "POST", body: { notes: notes ?? null } }),
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
  createIntent: (notes?: string) =>
    api<CreateIntentResponse>("/payments/create-intent", {
      method: "POST",
      body: { notes: notes ?? null },
    }),
  confirm: (orderId: string) =>
    api<{ payment_status: string; order_status: string; pi_status: string }>(
      `/payments/confirm/${orderId}`,
      { method: "POST" }
    ),
  status: (orderId: string) =>
    api<PaymentStatusResponse>(`/payments/status/${orderId}`),
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
