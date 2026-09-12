import { apiClient } from './client';
import type { LectureRead, LectureUpdate } from '@/types';

/** GET /lectures/ — получить список лекций организации */
export async function getLectures(): Promise<LectureRead[]> {
  const { data } = await apiClient.get<LectureRead[]>('/lectures/');
  return data;
}

/** GET /lectures/{id} — получить детали конкретной лекции */
export async function getLecture(id: string): Promise<LectureRead> {
  const { data } = await apiClient.get<LectureRead>(`/lectures/${id}`);
  return data;
}

/** POST /lectures/upload — загрузка файла лекции */
export async function uploadLecture(
  title: string,
  subjectId: string,
  file: File,
  openFrom?: string | null,      // FIX-7: ISO-строка или null
  deadlineAt?: string | null,    // FIX-7
  examDurationMinutes?: number | null, // FIX-7
): Promise<any> {
  const formData = new FormData();
  formData.append('title', title);
  formData.append('subject_id', subjectId);
  formData.append('file', file);
  if (openFrom)           formData.append('open_from', openFrom);
  if (deadlineAt)         formData.append('deadline_at', deadlineAt);
  if (examDurationMinutes != null)
    formData.append('exam_duration_minutes', String(examDurationMinutes));

  // НЕ задаём Content-Type вручную — axios сам добавит boundary
  const { data } = await apiClient.post('/lectures/upload', formData);
  return data;
}

/** POST /lectures/{id}/publish — перевод лекции в статус PUBLISHED */
export async function publishLecture(lectureId: string): Promise<any> {
  const { data } = await apiClient.post(`/lectures/${lectureId}/publish`);
  return data;
}

/** 
 * PATCH /lectures/{id} — обновление метаданных лекции 
 * (Название, дедлайны, статус)
 */
export async function updateLecture(id: string, payload: LectureUpdate): Promise<LectureRead> {
  const { data } = await apiClient.patch<LectureRead>(`/lectures/${id}`, payload);
  return data;
}

/** DELETE /lectures/{id} — полное удаление лекции */
export async function deleteLecture(id: string): Promise<void> {
  await apiClient.delete(`/lectures/${id}`);
}

/** 
 * GET /lectures/{id}/download — скачивание файла 
 * Используем responseType: 'blob' для обработки потока данных
 */
export async function downloadLectureFile(id: string, fileName: string): Promise<void> {
  const response = await apiClient.get(`/lectures/${id}/download`, {
    responseType: 'blob',
  });

  // Создаем невидимую ссылку для скачивания
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', fileName); // Имя файла будет подставлено из параметров
  document.body.appendChild(link);
  link.click();
  
  // Очистка ресурсов
  link.remove();
  window.URL.revokeObjectURL(url);
}
/** 
 * POST /lectures/{id}/regenerate — запуск повторной генерации вопросов.
 * Стирает старые вопросы и чанки, возвращает лекцию в статус PROCESSING.
 */
export async function regenerateLecture(id: string): Promise<LectureRead> {
  const { data } = await apiClient.post<LectureRead>(`/lectures/${id}/regenerate`);
  return data;
}