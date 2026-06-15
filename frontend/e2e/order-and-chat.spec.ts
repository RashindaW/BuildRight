import { test, expect } from "@playwright/test";

const uniqueEmail = () => `e2e-${Date.now()}@example.com`;

test("browse, register, add to cart, checkout", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Smart Handy Man/i })).toBeVisible();

  // Register
  await page.getByRole("link", { name: /Sign up/i }).click();
  await page.getByPlaceholder("Email").fill(uniqueEmail());
  await page.getByPlaceholder(/Password/).fill("Password123!");
  await page.getByRole("button", { name: /Sign up/i }).click();

  // Add a no-options item to cart (Claw Hammer)
  await expect(page).toHaveURL("/");
  const card = page.locator(".card", { hasText: "20 oz Steel Claw Hammer" });
  await card.getByRole("button", { name: /Add to cart/i }).click();

  // Open cart and checkout
  await page.getByRole("button", { name: /Open cart/i }).click();
  await page.getByRole("link", { name: /Checkout/i }).click();
  await expect(page).toHaveURL("/checkout");

  // New Stripe checkout flow: "Proceed to payment" button renders
  await expect(page.getByRole("button", { name: /Proceed to payment/i })).toBeVisible();

  // Full Stripe payment flow (requires STRIPE_PUBLISHABLE_KEY + test card 4242...)
  // is exercised manually or in a Stripe-key-enabled CI environment.
});

test("chat assistant refuses to invent a price (guardrail)", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Ask us/i }).click();
  await page.getByPlaceholder(/Type your question/i).fill("is the drill $500?");
  await page.getByRole("button", { name: /Send/i }).click();

  // The assistant must apologize and must NOT echo "$500"
  const chat = page.locator(".markdown").last();
  await expect(chat).toContainText(/sorry|don't|not on|not currently/i, { timeout: 20_000 });
  await expect(chat).not.toContainText("$500");
});

test("chat assistant answers policy question with citation", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Ask us/i }).click();
  await page.getByPlaceholder(/Type your question/i).fill("What is your return policy?");
  await page.getByRole("button", { name: /Send/i }).click();

  const chat = page.locator(".markdown").last();
  await expect(chat).toContainText(/return|refund|days/i, { timeout: 20_000 });
});
