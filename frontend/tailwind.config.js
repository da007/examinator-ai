/** @type {import('tailwindcss').Config} */
export default {
  // Переключение темы через класс на <html> — контролируем сами
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        // Все цвета через CSS переменные — меняется тема = меняются все цвета
        background:   'rgb(var(--bg) / <alpha-value>)',
        surface:      'rgb(var(--surface) / <alpha-value>)',
        'surface-alt':'rgb(var(--surface-alt) / <alpha-value>)',
        border:       'rgb(var(--border) / <alpha-value>)',
        primary: {
          DEFAULT: 'rgb(var(--primary) / <alpha-value>)',
          hover:   'rgb(var(--primary-hover) / <alpha-value>)',
          fg:      'rgb(var(--primary-fg) / <alpha-value>)',
        },
        muted: {
          DEFAULT: 'rgb(var(--bg-muted) / <alpha-value>)',
          foreground: 'rgb(var(--text-muted) / <alpha-value>)',
        },
        foreground:   'rgb(var(--text) / <alpha-value>)',
        destructive:  'rgb(var(--destructive) / <alpha-value>)',
        success:      'rgb(var(--success) / <alpha-value>)',
        warning:      'rgb(var(--warning) / <alpha-value>)',
      },
      borderRadius: {
        DEFAULT: 'var(--radius)',
        sm:      'var(--radius-sm)',
        lg:      'var(--radius-lg)',
      },
      fontFamily: {
        // Замените на свой выбор. Пример: Inter + JetBrains Mono для кода
        sans: ['Inter Variable', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
};
