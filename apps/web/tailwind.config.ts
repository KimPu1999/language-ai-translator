import type { Config } from "tailwindcss";

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: { sans: ["Inter", "Noto Sans Myanmar", "ui-sans-serif", "system-ui"] },
      colors: { ink: "#11233f", navy: "#102a56", mist: "#f5f8fc", sky: "#e9f2ff" },
      boxShadow: { soft: "0 18px 60px rgba(16, 42, 86, .10)" },
    },
  },
  plugins: [],
} satisfies Config;

