// ─── useThemeApplier ─────────────────────────────────────────────────────────
// Применяет dark/light класс к <html>. Вызывается один раз в корне приложения.
// Не нужен ThemeContext — всё через CSS переменные.

import { useEffect } from 'react';
import { useTheme } from '@/store/useAppStore';

export function useThemeApplier() {
  const theme = useTheme();

  useEffect(() => {
    const root = document.documentElement;
    const isDark =
      theme === 'dark' ||
      (theme === 'system' &&
        window.matchMedia('(prefers-color-scheme: dark)').matches);

    root.classList.toggle('dark', isDark);
  }, [theme]);
}

// ── Хук для подписки на системную тему ───────────────────────────────────────
export function useSystemThemeWatcher() {
  const theme = useTheme();

  useEffect(() => {
    if (theme !== 'system') return;

    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = () => {
      document.documentElement.classList.toggle('dark', mq.matches);
    };

    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, [theme]);
}
