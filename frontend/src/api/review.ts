import { apiClient } from './client';

export interface AppealCreate {
  sessionId: string;
  reason: string;
}

export interface AppealRead {
  id: string;
  sessionId: string;
  studentId: string;
  studentName?: string;  // Добавлено
  studentEmail?: string; // Добавлено
  reason: string;
  status: 'pending' | 'accepted' | 'rejected';
  teacherComment: string | null;
  createdAt: string;
  updatedAt: string;
}

/** POST /reviews/appeals — Подача апелляции студентом */
export async function submitAppeal(payload: AppealCreate): Promise<AppealRead> {
  const { data } = await apiClient.post<AppealRead>('/reviews/appeals', payload);
  return data;
}

/** GET /reviews/my-appeals — Список апелляций текущего студента */
export async function getMyAppeals(): Promise<AppealRead[]> {
  const { data } = await apiClient.get<AppealRead[]>('/reviews/my-appeals');
  return data;
}

/** GET /reviews/appeals — Список ВСЕХ апелляций организации (для преподавателя) */
export async function getAllAppeals(): Promise<AppealRead[]> {
  const { data } = await apiClient.get<AppealRead[]>('/reviews/appeals'); 
  return data;
}

/** GET /reviews/pending — Очередь сессий, требующих внимания ИИ/учителя */
export async function getPendingReviews(): Promise<any[]> {
  const { data } = await apiClient.get('/reviews/pending');
  return data;
}

/** PATCH /reviews/appeals/{id}/resolve — Решение по апелляции */
export async function resolveAppeal(
  id: string, 
  payload: { status: 'accepted' | 'rejected', teacherComment: string }
): Promise<AppealRead> {
  const { data } = await apiClient.patch<AppealRead>(`/reviews/appeals/${id}/resolve`, payload);
  return data;
}

/** POST /reviews/correct-answer — Ручное изменение оценки преподавателем */
export async function correctAnswer(payload: { 
  answerId: string; 
  newScore: number; 
  teacherComment?: string 
}): Promise<any> {
  const { data } = await apiClient.post('/reviews/correct-answer', payload);
  return data;
}