/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "Inter var",
          "Inter",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica",
          "Arial",
          "sans-serif",
        ],
      },
      colors: {
        // Industrial blue — sturdy, trustworthy, hardware-appropriate.
        brand: {
          50: "#eff6ff",
          100: "#dbeafe",
          200: "#bfdbfe",
          300: "#93c5fd",
          400: "#60a5fa",
          500: "#2563eb",
          600: "#1d4ed8",
          700: "#1e40af",
          800: "#1e3a8a",
          900: "#172554",
        },
        // Semantic tokens — replace the inline green/amber/red literals scattered in cards.
        success: { light: "#dcfce7", DEFAULT: "#16a34a", dark: "#15803d" },
        warning: { light: "#fef3c7", DEFAULT: "#d97706", dark: "#b45309" },
        danger: { light: "#fee2e2", DEFAULT: "#dc2626", dark: "#b91c1c" },
      },
      boxShadow: {
        card: "0 1px 2px 0 rgb(16 24 40 / 0.04), 0 1px 3px 0 rgb(16 24 40 / 0.06)",
        "card-hover": "0 8px 24px -6px rgb(16 24 40 / 0.12), 0 2px 6px -2px rgb(16 24 40 / 0.08)",
        soft: "0 2px 8px -2px rgb(16 24 40 / 0.08)",
        pop: "0 16px 40px -12px rgb(16 24 40 / 0.28)",
      },
      borderRadius: {
        xl2: "1rem",
      },
      keyframes: {
        "fade-in-up": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        "slide-in-right": {
          "0%": { transform: "translateX(100%)" },
          "100%": { transform: "translateX(0)" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
      },
      animation: {
        "fade-in-up": "fade-in-up 0.35s cubic-bezier(0.22, 1, 0.36, 1) both",
        "fade-in": "fade-in 0.25s ease-out both",
        "slide-in-right": "slide-in-right 0.28s cubic-bezier(0.22, 1, 0.36, 1) both",
      },
    },
  },
  plugins: [],
};
