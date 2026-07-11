/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        yard: {
          950: "#0A1320",
          900: "#0F1B2D",
          800: "#16263D",
          700: "#1F3450",
          600: "#2C4A6E",
          500: "#3D6491",
          100: "#E7ECF3",
          50: "#F5F7FA",
        },
        signal: {
          DEFAULT: "#FF9F1C",
          dark: "#E0810A",
          light: "#FFC069",
        },
        ok: {
          DEFAULT: "#1F9D55",
          light: "#E3F8EC",
        },
        warn: {
          DEFAULT: "#D64545",
          light: "#FCE8E8",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      borderRadius: {
        sm: "6px",
        DEFAULT: "10px",
        lg: "14px",
        xl: "20px",
      },
      boxShadow: {
        card: "0 1px 2px rgba(15, 27, 45, 0.06), 0 4px 16px rgba(15, 27, 45, 0.08)",
      },
    },
  },
  plugins: [],
};
