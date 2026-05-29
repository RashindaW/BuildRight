export interface OptionChoice {
  id: string;
  name: string;
  price_delta_cents: number;
  is_default: boolean;
  is_available: boolean;
}

export interface OptionGroup {
  id: string;
  name: string;
  min_select: number;
  max_select: number;
  required: boolean;
  choices: OptionChoice[];
}

export interface MenuItem {
  id: string;
  slug: string;
  name: string;
  description: string;
  price: number;
  price_cents: number;
  category: string;
  is_available: boolean;
  featured: boolean;
  image_url: string | null;
  dietary_tags: string[];
  allergens: string[];
  keywords: string[];
  calories: number | null;
  spice_level: number;
  prep_time_min: number | null;
  option_groups: OptionGroup[];
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface Category {
  id: string;
  slug: string;
  name: string;
  display_order: number;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: "customer" | "admin";
  is_active: boolean;
}

export interface CartItem {
  id: string;
  menu_item_id: string;
  name: string;
  slug: string;
  quantity: number;
  unit_price_cents: number;
  line_total_cents: number;
  options: string[];
}

export interface Cart {
  id: string;
  items: CartItem[];
  subtotal_cents: number;
  item_count: number;
}

export interface OrderItem {
  id: string;
  name_snapshot: string;
  unit_price_cents: number;
  quantity: number;
  line_total_cents: number;
  options: { name_snapshot: string; price_delta_cents: number }[];
}

export interface Order {
  id: string;
  order_number: string;
  status: string;
  subtotal_cents: number;
  total_cents: number;
  notes: string | null;
  created_at: string;
  items: OrderItem[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  pending?: boolean;
}
