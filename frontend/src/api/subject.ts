import { apiClient } from './client';

export interface SubjectRead {
  id: string;
  name: string;
  description: string | null;
  orgId: string;
  teacherId: string;
  teacherInfo?: {
    fullName: string;
    email: string;
    phone?: string | null;
    bio?: string | null;
  };
  createdAt: string;
}

/** 
 * GET /subjects/ — получить список дисциплин организации.
 * Теперь используется официальный эндпоинт бэкенда.
 */
export async function getSubjects(): Promise<SubjectRead[]> {
  const { data } = await apiClient.get<SubjectRead[]>('/subjects/');
  return data;
}

/** 
 * GET /subjects/{id} — детали дисциплины (опционально)
 */
export async function getSubject(id: string): Promise<SubjectRead> {
  const { data } = await apiClient.get<SubjectRead>(`/subjects/${id}`);
  return data;
}