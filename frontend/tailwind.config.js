/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#0F4C75',
          dark: '#1B262C',
          light: '#3282B8',
          subtle: '#BBE1FA',
        },
        navy: {
          DEFAULT: '#172B4D',
          dark: '#0A192F',
          light: '#253858',
        },
        sidebar: {
          DEFAULT: '#161F30',
          hover: '#1E2D47',
          border: '#23334E',
          active: '#0F4C75',
        },
        surface: {
          DEFAULT: '#FFFFFF',
          muted: '#F7F9FC',
          card: '#FFFFFF',
          border: '#E2E8F0',
        },
        status: {
          success: '#10B981',
          warning: '#F59E0B',
          danger: '#EF4444',
          info: '#3B82F6',
        }
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        outfit: ['Outfit', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
