/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef4ff",
          100: "#dce7fd",
          500: "#1e4fb8",
          600: "#1a3f96",
          700: "#16337a",
          800: "#122a63",
          900: "#0e2149",
        },
        saffron: "#FF9933",
        indiaGreen: "#138808",
      },
      fontFamily: {
        sans: [
          "Inter",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
      },
    },
  },
  plugins: [],
};
