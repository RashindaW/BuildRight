import { describe, expect, it } from "vitest";
import { sanitize } from "../../lib/sanitize";

describe("sanitize", () => {
  it("strips script tags from AI output", () => {
    const out = sanitize("<p>hi</p><script>alert(1)</script>");
    expect(out).toContain("hi");
    expect(out).not.toContain("<script>");
  });
});
