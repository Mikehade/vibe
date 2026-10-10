/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          950: '#08080a',
          900: '#0d0d10',
          850: '#131317',
          800: '#1a1a1f',
          700: '#26262d',
          600: '#34343c',
        },
        paper: {
          DEFAULT: '#f4f1ea',
          muted: '#a8a39a',
          faint: '#6f6b64',
        },
        amber: { DEFAULT: '#e8b04b', soft: '#f3cf85', deep: '#b9822a' },
        role: {
          opener: '#8cc0ad',
          main: '#e8b04b',
          bridge: '#a99be0',
          nightcap: '#7f9fdc',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
        serif: ['"Instrument Serif"', 'Georgia', 'serif'],
      },
      letterSpacing: { label: '0.16em' },
      transitionTimingFunction: { out: 'cubic-bezier(0.2, 0.8, 0.2, 1)' },
    },
  },
  plugins: [],
};
