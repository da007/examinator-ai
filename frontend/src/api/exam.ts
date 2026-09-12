// ─── Exam API ─────────────────────────────────────────────────────────────────
// Покрывает /exams/* эндпоинты бэкенда.
// Бэкенд возвращает camelCase (alias_generator=to_camel) — принимаем as-is.

import { apiClient } from './client';
import type {
  ExamSessionRead,
  ExamSessionUpdateDraft,
  ExamResultRead,
} from '@/types';

const BASE = '/exams';

/** POST /exams/sessions — начать новую сессию */
export async function createSession(lectureId: string): Promise<ExamSessionRead> {
  const { data } = await apiClient.post<ExamSessionRead>(`${BASE}/start`, { // <--- ЗАМЕНИЛИ /sessions на /start
    lectureId,
  });
  return data;
}

/** GET /exams/sessions/{id} — получить текущую сессию (polling) */
export async function getSession(sessionId: string): Promise<ExamSessionRead> {
  const { data } = await apiClient.get<ExamSessionRead>(
    `${BASE}/sessions/${sessionId}`,
  );
  return data;
}

/**
 * PATCH /exams/sessions/{id}/draft — автосохранение.
 * Реализует Optimistic Locking: бэкенд вернёт 409, если version устарела.
 * Возвращает обновлённую сессию с новой version.
 */
export async function patchDraft(
  sessionId: string,
  payload: ExamSessionUpdateDraft,
): Promise<ExamSessionRead> {
  const { data } = await apiClient.patch<ExamSessionRead>(
    `${BASE}/sessions/${sessionId}/draft`,
    payload,
  );
  return data;
}

/** POST /exams/sessions/{id}/submit — финальная сдача */
export async function submitSession(
  sessionId: string,
  finalDraft?: Record<string, unknown>,
): Promise<ExamSessionRead> {
  const { data } = await apiClient.post<ExamSessionRead>(
    `${BASE}/sessions/${sessionId}/submit`,
    { finalDraft: finalDraft ?? null },
  );
  return data;
}

/** GET /exams/sessions/{id}/result — результаты после grading */
export async function getResult(sessionId: string): Promise<ExamResultRead> {
  const { data } = await apiClient.get<ExamResultRead>(
    `${BASE}/sessions/${sessionId}/result`,
  );
  return data;
}

/** GET /exams/sessions — история сессий студента */
export async function getMySessions(): Promise<ExamSessionRead[]> {
  const { data } = await apiClient.get<ExamSessionRead[]>(`${BASE}/sessions`);
  return data;
}
