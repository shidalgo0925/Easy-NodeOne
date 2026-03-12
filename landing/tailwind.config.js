/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: '#1E3A8A',
        secondary: '#2563EB',
        cyan: '#06B6D4',
        accent: '#14B8A6',
        'gray-dark': '#0F172A',
        'gray-mid': '#334155',
        'gray-light': '#F1F5F9',
        gradient: { start: '#2563EB', end: '#06B6D4' },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      backgroundImage: {
        'gradient-official': 'linear-gradient(135deg, #2563EB 0%, #06B6D4 100%)',
        'gradient-radial': 'radial-gradient(ellipse at 50% 0%, rgba(37, 99, 235, 0.08) 0%, transparent 55%)',
      },
      boxShadow: {
        'soft': '0 4px 24px -4px rgba(37, 99, 235, 0.12)',
        'glow': '0 0 40px -8px rgba(37, 99, 235, 0.4)',
        'card-hover': '0 24px 48px -12px rgba(30, 58, 138, 0.15)',
      },
      animation: {
        'float': 'float 6s ease-in-out infinite',
      },
      keyframes: {
        float: { '0%, 100%': { transform: 'translateY(0)' }, '50%': { transform: 'translateY(-12px)' } },
      },
    },
  },
  plugins: [],
}
