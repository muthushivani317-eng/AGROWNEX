/** @type {import('tailwindcss').Config} */
const withOpacity = (variable) => `rgb(var(${variable}) / <alpha-value>)`;

module.exports = {
  darkMode: 'class',
  content: [
    './app/**/*.{js,jsx,ts,tsx}',
    './components/**/*.{js,jsx,ts,tsx}',
    './features/**/*.{js,jsx,ts,tsx}',
    './providers/**/*.{js,jsx,ts,tsx}',
  ],
  presets: [require('nativewind/preset')],
  theme: {
    extend: {
      colors: {
        // Brand
        primary: {
          DEFAULT: withOpacity('--color-primary'),
          light: withOpacity('--color-primary-light'),
          dark: withOpacity('--color-primary-dark'),
        },
        // Semantic
        success: withOpacity('--color-success'),
        warning: withOpacity('--color-warning'),
        danger: withOpacity('--color-danger'),
        info: withOpacity('--color-info'),
        // Surfaces
        bg: withOpacity('--color-bg'),
        surface: {
          DEFAULT: withOpacity('--color-surface'),
          card: withOpacity('--color-card'),
        },
        border: withOpacity('--color-border'),
        // Text
        content: {
          DEFAULT: withOpacity('--color-text'),
          muted: withOpacity('--color-text-muted'),
          disabled: withOpacity('--color-text-disabled'),
        },
        'on-primary': withOpacity('--color-on-primary'),
      },
      borderRadius: {
        sm: '8px',
        md: '12px',
        lg: '20px',
        card: '24px',
        full: '999px',
      },
      fontFamily: {
        sans: ['Inter_400Regular'],
        medium: ['Inter_500Medium'],
        semibold: ['Inter_600SemiBold'],
        bold: ['Inter_700Bold'],
        tamil: ['NotoSansTamil_400Regular'],
        'tamil-medium': ['NotoSansTamil_500Medium'],
        'tamil-semibold': ['NotoSansTamil_600SemiBold'],
        'tamil-bold': ['NotoSansTamil_700Bold'],
      },
    },
  },
  plugins: [],
};
