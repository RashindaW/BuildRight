import { describe, expect, it } from "vitest";
import { formatPrice, imageSrc } from "./format";

describe("formatPrice", () => {
  it("formats cents as $X.XX matching the backend", () => {
    expect(formatPrice(450)).toBe("$4.50");
    expect(formatPrice(1150)).toBe("$11.50");
    expect(formatPrice(0)).toBe("$0.00");
  });
});

describe("imageSrc", () => {
  it("falls back to placeholder", () => {
    expect(imageSrc(null)).toBe("/img/_placeholder.svg");
  });
  it("passes through absolute URLs", () => {
    expect(imageSrc("https://x/y.png")).toBe("https://x/y.png");
  });
  it("prefixes relative filenames", () => {
    expect(imageSrc("latte.png")).toBe("/img/latte.png");
  });
});
