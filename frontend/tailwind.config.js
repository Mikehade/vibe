/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        vibe: {
          bg: '#0a0a0f',
          surface: '#14141f',
          card: '#1c1c2e',
          border: '#2a2a3e',
          accent: '#6c5ce7',
          'accent-light': '#a29bfe',
          text: '#e8e8f0',
          'text-muted': '#8888a0',
          success: '#00b894',
          warning: '#fdcb6e',
          danger: '#e17055',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      // Fire TV 10-foot UI — larger tap/focus targets
      spacing: {
        tv: '2.5rem',
        'tv-lg': '4rem',
      },
      fontSize: {
        'tv-sm': ['1.125rem', '1.5rem'],
        'tv-base': ['1.375rem', '1.875rem'],
        'tv-lg': ['1.75rem', '2.25rem'],
        'tv-xl': ['2.25rem', '2.75rem'],
        'tv-2xl': ['3rem', '3.5rem'],
      },
      borderRadius: {
        tv: '1rem',
      },
    },
  },
  plugins: [],
};
