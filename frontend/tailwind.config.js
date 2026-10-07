/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        black: '#0a0a0a',
        gold: '#c9a84c',
        'gold-light': '#e0c97a',
        'gold-dark': '#a8893a',
        ivory: '#FDFBF5',
        cream: '#FBF7EA',
        beige: '#F8F1DD',
        green: '#1EBE53',
        blue: '#1A6F9E',
        border: '#e8dcc8',
      },
    },
  },
  plugins: [],
}