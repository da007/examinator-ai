import { apiClient } from './client';
import type { QuestionRead, QuestionUpdate } from '@/types';

/** GET /questions/lecture/{id} — все вопросы лекции */
export async function getQuestionsByLecture(lectureId: string): Promise<QuestionRead[]> {
  const { data } = await apiClient.get<QuestionRead[]>(`/questions/lecture/${lectureId}`);
  return data;
}

/** PATCH /questions/{id} — обновление вопроса и тезисов */
export async function updateQuestion(id: string, payload: QuestionUpdate): Promise<QuestionRead> {
  const { data } = await apiClient.patch<QuestionRead>(`/questions/${id}`, payload);
  return data;
}

/** DELETE /questions/{id} — удаление вопроса */
export async function deleteQuestion(id: string): Promise<void> {
  await apiClient.delete(`/questions/${id}`);
}

/** POST /questions/{id}/recalculate — запуск массового пересчета баллов студентов по вопросу */
export async function recalculateQuestionScores(id: string): Promise<{ message: string }> {
  const { data } = await apiClient.post(`/questions/${id}/recalculate`);
  return data;
}
/** POST /questions/lecture/{id} — ручное создание вопроса */
export async function createQuestion(lectureId: string, payload: QuestionUpdate): Promise<QuestionRead> {
  const { data } = await apiClient.post<QuestionRead>(`/questions/lecture/${lectureId}`, payload);
  return data;
}