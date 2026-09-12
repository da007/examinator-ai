// ─── Domain Types — зеркало Pydantic-схем бэкенда ───────────────────────────
// Бэкенд отдаёт camelCase (alias_generator=to_camel в APIModel).
// Здесь храним ДОМЕННЫЕ модели (не DTO). Маппинг DTO→Domain — в domain/mappers.ts

// ── Auth ─────────────────────────────────────────────────────────────────────

export type UserRole = 'admin' | 'teacher' | 'ta' | 'student';

export interface AuthUser {
  id: string;
  email: string;
  fullName: string | null;
  role: UserRole;
  orgId: string;
  isActive: boolean;
  createdAt: string;phone?: string | null;
  bio?: string | null;
}

export interface TokenResponse {
  accessToken: string;
  tokenType: string;
}

// ── Lecture ───────────────────────────────────────────────────────────────────

export type LectureStatus =
  | 'draft'
  | 'uploaded'
  | 'processing'
  | 'generating'
  | 'review_required'
  | 'published'
  | 'archived';

export interface LectureShort {
  id: string;
  title: string;
  status: LectureStatus;
  createdAt: string;
}

export interface LectureRead extends LectureShort {
  orgId: string;
  subjectId: string;
  teacherId: string | null;
  version: number;
  openFrom: string | null;
  deadlineAt: string | null;
  examDurationMinutes: number | null; // FIX-6
  updatedAt: string;
}

export interface LectureUpdate {
  title?: string;
  openFrom?: string | null;
  deadlineAt?: string | null;
  examDurationMinutes?: number | null; // FIX-6
  status?: LectureStatus;
}

// ── Questions ─────────────────────────────────────────────────────────────────

export type QuestionType = 'open_ended' | 'formula';

export interface QuestionShort {
  id: string;
  questionText: string;
  questionType: QuestionType;
  difficulty: string;
}

// ── Exam Session ──────────────────────────────────────────────────────────────

export type SessionStatus =
  | 'active'
  | 'submitted'
  | 'processing'
  | 'completed'
  | 'cancelled';

export interface FormulaData {
  raw: string;
  latex: string;
  normalized: string | null;
}

/** Один ответ из current_draft: { [questionId]: DraftAnswer } */
export interface DraftAnswer {
  text: string;
  formula?: FormulaData;
}

/** Полная сессия — приходит с GET /exams/sessions/{id} */
export interface ExamSessionRead {
  id: string;
  lectureId: string;
  status: SessionStatus;
  version: number;
  startTime: string;
  endTime: string | null;
  questions: QuestionShort[];
  currentDraft: Record<string, DraftAnswer>;
  /**
   * ИСПРАВЛЕНО: поле добавлено в тип.
   * Бэкенд проставляет true, если система обнаружила аномальное сходство с источниками.
   * Используется в ExamResultPage для отображения предупреждения преподавателю.
   */
  isSuspicious?: boolean;
}

/** Тело PATCH /exams/sessions/{id}/draft */
export interface ExamSessionUpdateDraft {
  version: number;
  currentDraft: Record<string, DraftAnswer>;
}

/** Результат после grading */
export interface StudentAnswerRead {
  id: string;          // ИСПРАВЛЕНО: поле было неявным (answer.id), теперь явно в типе
  questionId: string;
  answerText: string;
  formulaData: FormulaData | null;
  finalScore: number | null;
  confidenceScore: number | null;
  aiExplanation: string | null;
  referenceAnswer?: string | null;
}

export interface ExamResultRead {
  sessionId: string;
  status: SessionStatus;
  totalScore: number | null;
  answers: StudentAnswerRead[];
}

// ── Analytics ─────────────────────────────────────────────────────────────────

export interface StudentProgress {
  avgScore: number;
  examsCompleted: number;
  strongTopics: string[];
  weakTopics: string[];
  scoreHistory: number[];
}

export interface TeacherDashboard {
  totalStudents: number;
  activeSubjects: number;
  activeLectures: number;
  pendingReviewsCount: number;
  pendingAppealsCount: number;
  totalSuspiciousCount: number;
  recentActivity: Array<Record<string, unknown>>;
}

export interface QuestionRead extends QuestionShort {
  chunkId: string;
  referenceAnswer: string;
  keyTheses: Array<{ text: string; importance: number }>;
  createdAt: string;
  updatedAt: string;
}

export interface QuestionUpdate {
  questionText?: string;
  referenceAnswer?: string;
  keyTheses?: Array<{ text: string; importance: number }>;
  difficulty?: string;
  questionType?: QuestionType;
}