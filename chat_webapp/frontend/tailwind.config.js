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
          DEFAULT: '#2b8cee',
          hover: '#1E7CE5',
          light: 'rgba(43, 140, 238, 0.1)',
        },
        background: {
          DEFAULT: '#FFFFFF',
          light: '#f6f7f8',
          signup: 'rgba(43, 140, 238, 0.1)',
          secondary: '#F5F7FA',
        },
        text: {
          primary: '#1F2937',
          secondary: '#6B7280',
          muted: '#9CA3AF',
        },
        border: {
          DEFAULT: '#E5E7EB',
        },
        success: '#10B981',
        error: '#EF4444',
      },
      fontFamily: {
        display: ['Plus Jakarta Sans', 'Noto Sans', 'sans-serif'],
      },
      borderRadius: {
        DEFAULT: '0.25rem',
        lg: '0.5rem',
        xl: '0.75rem',
        full: '9999px',
      },
    },
  },
  plugins: [
    function({ addUtilities }) {
      addUtilities({
        '.text-primary': { color: '#2b8cee' },
        '.bg-primary': { backgroundColor: '#2b8cee' },
        '.border-primary': { borderColor: '#2b8cee' },
        '.ring-primary': { '--tw-ring-color': '#2b8cee' },
        '.hover\\:bg-primary-hover:hover': { backgroundColor: '#1E7CE5' },
        '.bg-primary-light': { backgroundColor: 'rgba(43, 140, 238, 0.1)' },
        '.ring-primary-light': { '--tw-ring-color': 'rgba(43, 140, 238, 0.1)' },
        '.bg-background-light': { backgroundColor: '#f6f7f8' },
        '.bg-background-signup': { backgroundColor: 'rgba(43, 140, 238, 0.1)' },
        '.bg-background-secondary': { backgroundColor: '#F5F7FA' },
        '.text-text-primary': { color: '#1F2937' },
        '.text-text-secondary': { color: '#6B7280' },
        '.text-text-muted': { color: '#9CA3AF' },
        '.border-border': { borderColor: '#E5E7EB' },
        '.bg-success': { backgroundColor: '#10B981' },
        '.text-success': { color: '#10B981' },
        '.bg-error': { backgroundColor: '#EF4444' },
        '.text-error': { color: '#EF4444' },
      });
    },
  ],
}

