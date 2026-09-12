// ─── Session Transport ────────────────────────────────────────────────────────
// Абстракция над сетевым слоем. Сейчас — polling через React Query.
// Завтра — меняем только этот файл, UI не трогаем.
//
// Возвращает унифицированный интерфейс: { session, isLoading, isSyncing, refresh }

import { useQuery } from '@tanstack/react-query';
import { getSession } from '@/api/exam';
import { APP_CONFIG } from '@/config/app';
import type { ExamSessionRead } from '@/types';

export interface TransportState {
  session: ExamSessionRead | undefined;
  isLoading: boolean;
  /** true когда фоновый refetch активен (показываем cloud spinner) */
  isSyncing: boolean;
  error: Error | null;
  refresh: () => void;
}

export function useSessionTransport(sessionId: string): TransportState {
  const query = useQuery({
    queryKey: ['exam-session', sessionId],
    queryFn: () => getSession(sessionId),

    // Polling: активен пока бэкенд обрабатывает (Celery grading task)
    refetchInterval: (q) => {
      const status = q.state.data?.status;
      if (status === 'processing' || status === 'submitted') {
        return APP_CONFIG.gradingPollingIntervalMs;
      }
      // Лёгкий фоновый polling на active-сессии для синхронизации вкладок
      if (status === 'active') {
        return 15_000;
      }
      return false;
    },

    staleTime: 5_000,
    retry: 2,
  });

  return {
    session: query.data,
    isLoading: query.isLoading,
    isSyncing: query.isFetching && !query.isLoading,
    error: query.error as Error | null,
    refresh: query.refetch,
  };
}
