/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0f172a",
        glow: "#8b5cf6",
        aqua: "#22d3ee",
      },
    },
  },
  plugins: [],
};
