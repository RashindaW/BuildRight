import DOMPurify from "dompurify";

/** Sanitize HTML produced from AI markdown before rendering. */
export function sanitize(html: string): string {
  return DOMPurify.sanitize(html, { USE_PROFILES: { html: true } });
}
