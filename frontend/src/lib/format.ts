/** Single source of price formatting — mirrors the backend's $X.XX. */
export function formatPrice(cents: number): string {
  return `$${(cents / 100).toFixed(2)}`;
}

export const DIETARY_LABELS: Record<string, string> = {
  vegan: "Vegan",
  vegetarian: "Vegetarian",
  "gluten-free": "Gluten-Free",
  "dairy-free": "Dairy-Free",
  "contains-nuts": "Contains Nuts",
};

export const ALLERGEN_LABELS: Record<string, string> = {
  gluten: "Gluten",
  dairy: "Dairy",
  egg: "Egg",
  soy: "Soy",
  "tree-nuts": "Tree Nuts",
  peanuts: "Peanuts",
  shellfish: "Shellfish",
  fish: "Fish",
  sesame: "Sesame",
};

export function imageSrc(url: string | null): string {
  if (!url) return "/img/_placeholder.svg";
  if (url.startsWith("http")) return url;
  return `/img/${url}`;
}
