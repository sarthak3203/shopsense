import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        navy: '#1E2761',
        ice: '#CADCFC',
        ink: '#14203a',
        success: '#24785a',
        amber: '#E8A33D',
      },
      fontFamily: {
        display: ['Georgia', 'Cambria', '"Times New Roman"', 'serif'],
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        panel: '0 8px 24px rgba(30, 39, 97, 0.08)',
      },
    },
  },
  plugins: [],
} satisfies Config
