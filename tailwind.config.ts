import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50:  "#f0f7e6",
          100: "#dcefc9",
          200: "#b9df93",
          300: "#96cf5d",
          400: "#73bf27",
          500: "#5aa01e",
          600: "#2d5016",
          700: "#243f12",
          800: "#1b2f0d",
          900: "#121f09",
        },
        accent: {
          DEFAULT: "#f5a623",
          light:   "#ffc85c",
          dark:    "#c07d10",
        },
        earth: {
          50:  "#fdf8f0",
          100: "#faefd8",
          200: "#f3d9a4",
          300: "#ecc370",
          400: "#e5ad3c",
          500: "#c8901a",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        arabic: ["var(--font-arabic)", "Noto Naskh Arabic", "Arial", "sans-serif"],
      },
      animation: {
        "fade-in":    "fadeIn 0.6s ease-out forwards",
        "slide-up":   "slideUp 0.6s ease-out forwards",
        "slide-in-r": "slideInRight 0.6s ease-out forwards",
        "slide-in-l": "slideInLeft 0.6s ease-out forwards",
      },
      keyframes: {
        fadeIn: {
          "0%":   { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%":   { opacity: "0", transform: "translateY(30px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideInRight: {
          "0%":   { opacity: "0", transform: "translateX(30px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        slideInLeft: {
          "0%":   { opacity: "0", transform: "translateX(-30px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
