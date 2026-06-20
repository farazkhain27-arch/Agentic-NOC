/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        noc: {
          dark: '#0B0F19',
          card: '#111827',
          border: '#1F2937',
          critical: '#EF4444',
          high: '#F97316',
          memo: '#EAB308',
          info: '#3B82F6',
          ok: '#22C55E',
        }
      }
    }
  },
  plugins: [],
}
