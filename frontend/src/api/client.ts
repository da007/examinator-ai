// ─── API Client — Axios + Auth Interceptors ──────────────────────────────────
// Один экземпляр на всё приложение. Токен инжектируется перед каждым запросом.
// При 401 — автоматический разлогин (токен истёк или невалиден).

import axios from 'axios';
import { APP_CONFIG } from '@/config/app';
import { notify } from '@/store/useNotificationStore';

export const apiClient = axios.create({
  baseURL: APP_CONFIG.apiBaseUrl,
});

// ── Request: добавляем Bearer токен ──────────────────────────────────────────
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Хелпер для извлечения сообщения об ошибке ────────────────────────────────
export function getApiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    // FastAPI отдаёт { detail: string | [{msg, loc}] }
    const detail = (error.response?.data as { detail?: unknown })?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) return detail.map((d) => d.msg).join('; ');
  }
  return 'Произошла неизвестная ошибка';
}

// ── Response: обрабатываем ошибки ────────────────────────────────────────────
apiClient.interceptors.response.use(
  (res) => res,
  (error) => {
    const status = error.response?.status;

    if (status === 401) {
      // ИСПРАВЛЕНО: токен истёк — разлогиниваем пользователя.
      // Импортируем лениво через getState(), чтобы избежать циклической зависимости
      // (store → client → store).
      import('@/store/useAppStore').then(({ useAppStore }) => {
        useAppStore.getState().logout();
      });
      notify('error', 'Сессия истекла. Пожалуйста, войдите снова.');
    } else if (error.response?.status === 409) {
      notify('error', 'Конфликт версий! Данные будут обновлены.');
    } else if (error.code === 'ERR_NETWORK') {
      notify('error', 'Проблемы с интернет-соединением.');
    }

    return Promise.reject(error);
  },
);