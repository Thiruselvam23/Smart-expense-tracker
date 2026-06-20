/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: { DEFAULT: '#1E3A5F', light: '#2E5082', dark: '#152B47' },
        accent:  { DEFAULT: '#2E86AB', light: '#4AA3C5', dark: '#1E6A8A' },
      },
      fontFamily: { sans: ['Inter', 'system-ui', 'sans-serif'] },
    },
  },
  plugins: [],
}
