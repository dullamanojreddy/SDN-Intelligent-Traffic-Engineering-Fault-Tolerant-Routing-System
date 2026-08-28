/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        cyber: {
          bg: "#0B0C10",
          card: "#12141D",
          cardLighter: "#181B26",
          border: "#232738",
          purple: "#7C3AED",
          purpleGlow: "#8B5CF6",
          accent: "#6366F1",
          neonGreen: "#10B981",
          neonRed: "#EF4444",
          neonYellow: "#F59E0B"
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['Fira Code', 'Courier New', 'monospace']
      }
    },
  },
  plugins: [],
}
