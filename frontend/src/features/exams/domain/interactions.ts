// ─── Interaction Protocol ─────────────────────────────────────────────────────
// Unified Interaction Model — основа таймлайна.

import type { QuestionShort, DraftAnswer, SessionStatus } from '@/types';

// ── Discriminated Union ───────────────────────────────────────────────────────

export interface QuestionInteraction {
  kind: 'question';
  id: string;
  timestamp: number;
  question: QuestionShort;
  index: number; // порядковый номер (1-based) для отображения
}

export interface AnswerInteraction {
  kind: 'answer';
  id: string;
  timestamp: number;
  questionId: string;
  draft: DraftAnswer;
  syncStatus: SyncStatus;
  /** true — ответ загружен с сервера (прошлая сессия), false — только что отправлен */
  isHistorical: boolean;
}

export interface SystemInteraction {
  kind: 'system';
  id: string;
  timestamp: number;
  message: string;
  variant?: 'info' | 'success' | 'warning' | 'error';
}

export interface StatusInteraction {
  kind: 'status';
  id: string;
  timestamp: number;
  label: string;
  statusType: 'typing' | 'saving' | 'grading' | 'error';
}

export interface EventInteraction {
  kind: 'event';
  id: string;
  timestamp: number;
  label: string;
  severity: 'info' | 'warning' | 'error';
}

/**
 * Эфемерный пузырь — показывает текст который студент набирает,
 * но ещё не отправил. Исчезает после отправки.
 */
export interface DraftPreviewInteraction {
  kind: 'draft_preview';
  id: 'draft-preview-ephemeral'; // всегда один, стабильный ключ
  timestamp: number;
  questionId: string;
  text: string;
}

export type Interaction =
  | QuestionInteraction
  | AnswerInteraction
  | SystemInteraction
  | StatusInteraction
  | EventInteraction
  | DraftPreviewInteraction;

// ── Sync State ────────────────────────────────────────────────────────────────

export type SyncStatus = 'synced' | 'pending' | 'error';

// ── Session Lifecycle ─────────────────────────────────────────────────────────

export type SessionLifecycle =
  | 'initializing'
  | 'ready'
  | 'answering'
  | 'syncing'
  | 'submitting'
  | 'processing'
  | 'completed'
  | 'error';

export function sessionStatusToLifecycle(status: SessionStatus): SessionLifecycle {
  const map: Record<SessionStatus, SessionLifecycle> = {
    active:     'ready',
    submitted:  'processing',
    processing: 'processing',
    completed:  'completed',
    cancelled:  'error',
  };
  return map[status] ?? 'initializing';
}
