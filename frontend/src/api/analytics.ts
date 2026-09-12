import { apiClient } from './client';
import type { TeacherDashboard, StudentProgress } from '@/types';

export interface LectureAnalytics {
  totalExams: number;
  attendance: number;
  gradeDistribution: {
    bins: string[];
    counts: number[];
  } | null;
  topicMastery: Array<{ topicName: string; avgScore: number }> | null;
  killerQuestions: Array<{ questionId: string; successRate: number; questionText: string }> | null;
  aiMetrics: {
    avgConfidence: number;
    avgProcessingTime: number;
  } | null;
}

/** GET /analytics/lecture/{id} — детальная статистика лекции */
export async function getLectureAnalytics(lectureId: string): Promise<LectureAnalytics> {
  const { data } = await apiClient.get<LectureAnalytics>(`/analytics/lecture/${lectureId}`);
  return data;
}


/** GET /analytics/dashboard — сводные данные для преподавателя */
export async function getTeacherDashboard(): Promise<TeacherDashboard> {
  const { data } = await apiClient.get<TeacherDashboard>('/analytics/dashboard');
  return data;
}

/** GET /analytics/student/me — личный прогресс студента */
export async function getMyProgress(): Promise<StudentProgress> {
  const { data } = await apiClient.get<StudentProgress>('/analytics/student/me');
  return data;
}

/** 
 * GET /analytics/subjects/{id}/export — Скачать ведомость дисциплины (Excel)
 */
export async function exportSubjectGrades(subjectId: string, subjectName: string): Promise<void> {
  const response = await apiClient.get(`/analytics/subjects/${subjectId}/export`, {
    responseType: 'blob',
  });

  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', `Ведомость_${subjectName}.xlsx`);
  document.body.appendChild(link);
  link.click();
  
  link.remove();
  window.URL.revokeObjectURL(url);
}