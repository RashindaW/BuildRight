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
        // Industrial slate — machined gunmetal steel; serious, premium, hardware-grade.
        brand: {
          50: "#f5f7fa",
          100: "#e9edf2",
          200: "#cdd6e0",
          300: "#a7b5c4",
          400: "#7689a0",
          500: "#51647d",
          600: "#3b4d63",
          700: "#2e3d50",
          800: "#232f3e",
          900: "#161e29",
        },
        // Safety amber — the hi-vis accent for CTAs + "AI is live" highlights.
        // Use brand-900 (dark) text on the DEFAULT amber; accent-700 for amber text on white.
        accent: {
          light: "#fef3c7",
          DEFAULT: "#f59e0b",
          600: "#d97706",
          700: "#b45309",
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
