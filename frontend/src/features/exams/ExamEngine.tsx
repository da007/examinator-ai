// ─── ExamEngine — Точка входа ─────────────────────────────────────────────────
// Тонкий оркестратор: получает данные из useExamSession,
// роутит к нужному View. Никакой логики здесь нет — только склейка.

import React from 'react';
import { useExamSession } from './hooks/useExamSession';
import { useExamViewMode } from '@/store/useAppStore';

// Лениво загружаем оба View — студент не скачивает лишний бандл
const ChatExamView = React.lazy(() =>
  import('./views/ChatExamView').then((m) => ({ default: m.ChatExamView })),
);
const StandardExamView = React.lazy(() =>
  import('./views/StandardExamView').then((m) => ({ default: m.StandardExamView })),
);

interface ExamEngineProps {
  sessionId: string;
}

export function ExamEngine({ sessionId }: ExamEngineProps) {
  const examViewMode = useExamViewMode();
  const examState = useExamSession(sessionId);

  if (examState.lifecycle === 'initializing') {
    return (
      <div className="flex h-screen items-center justify-center">
        <p className="text-muted-foreground animate-pulse">Загрузка экзамена…</p>
      </div>
    );
  }

  if (examState.lifecycle === 'error') {
    return (
      <div className="flex h-screen items-center justify-center">
        <p className="text-destructive">Ошибка загрузки. Обновите страницу.</p>
      </div>
    );
  }

  return (
    <React.Suspense
      fallback={
        <div className="flex h-screen items-center justify-center">
          <p className="text-muted-foreground animate-pulse">Инициализация…</p>
        </div>
      }
    >
      {examViewMode === 'chat' ? (
        <ChatExamView {...examState} />
      ) : (
        <StandardExamView {...examState} />
      )}
    </React.Suspense>
  );
}
