import { test, expect } from "@playwright/test";

const uniqueEmail = () => `e2e-${Date.now()}@example.com`;

test("browse, register, add to cart, checkout", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Cut & Dry Cafe/i })).toBeVisible();

  // Register
  await page.getByRole("link", { name: /Sign up/i }).click();
  await page.getByPlaceholder("Email").fill(uniqueEmail());
  await page.getByPlaceholder(/Password/).fill("Password123!");
  await page.getByRole("button", { name: /Sign up/i }).click();

  // Add a no-options item to cart (Fresh Lemonade)
  await expect(page).toHaveURL("/");
  const card = page.locator(".card", { hasText: "Fresh Lemonade" });
  await card.getByRole("button", { name: /Add to cart/i }).click();

  // Open cart and checkout
  await page.getByRole("button", { name: /Open cart/i }).click();
  await page.getByRole("link", { name: /Checkout/i }).click();
  await expect(page).toHaveURL("/checkout");
  await page.getByRole("button", { name: /Place order/i }).click();

  // Confirmation
  await expect(page.getByText(/Order placed/i)).toBeVisible();
});

test("chat assistant refuses to invent a price (guardrail)", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Ask us/i }).click();
  await page.getByPlaceholder(/Type your question/i).fill("is the burger $50?");
  await page.getByRole("button", { name: /Send/i }).click();

  // The assistant must apologize and must NOT echo "$50"
  const chat = page.locator(".markdown").last();
  await expect(chat).toContainText(/sorry|don't|not on|not currently/i, { timeout: 20_000 });
  await expect(chat).not.toContainText("$50");
});
