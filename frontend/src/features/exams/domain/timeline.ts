import type { ExamSessionRead, DraftAnswer } from '@/types';
import type { Interaction, StatusInteraction, SyncStatus } from './interactions';

// ── Приветствия (стабильный выбор на основе startTime) ────────────────────────

const GREETINGS = [
  'Здравствуйте! Я ваш ИИ-экзаменатор. Давайте проверим ваши знания. Удачи!',
  'Приветствую. Надеюсь, вы хорошо подготовились. Ни пуха, ни пера!',
  'Добрый день. Приступим к тестированию. Постарайтесь отвечать полно. Удачи!',
];

function pluralQ(n: number): string {
  const m10 = n % 10, m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return 'вопрос';
  if (m10 >= 2 && m10 <= 4 && (m100 < 10 || m100 >= 20)) return 'вопроса';
  return 'вопросов';
}

// ── Основной строитель ────────────────────────────────────────────────────────
//
// Принципы:
//  1. localDraft — единственный источник правды для последовательного раскрытия.
//     session.currentDraft используется ТОЛЬКО для isHistorical-флага.
//  2. Вопрос N+1 появляется строго после того, как в localDraft есть ответ на N.
//  3. typingText → DraftPreviewInteraction (эфемерный пузырь пока юзер печатает).
//  4. Нет случайных реакций — таймлайн детерминирован.

export function buildTimeline({
  session,
  localDraft,
  syncStatus,
  activeQuestionId,
  ephemeral = [],
  typingText = '',
}: {
  session: ExamSessionRead;
  localDraft: Record<string, DraftAnswer>;
  syncStatus: Record<string, SyncStatus>;
  activeQuestionId: string | null;
  ephemeral?: StatusInteraction[];
  typingText?: string;
}): Interaction[] {
  const baseTs = new Date(session.startTime).getTime();
  const items: Interaction[] = [];
  const totalQ = session.questions.length;

  // Стабильный RNG на основе startTime
  const rng = (max: number, salt: number) =>
    Math.floor(Math.abs(Math.sin(baseTs * 0.001 + salt)) * 10_000) % max;

  // ── Приветствие ──────────────────────────────────────────────────────────────
  items.push({
    kind: 'system',
    id: `greet-${session.id}`,
    timestamp: baseTs - 2000,
    message: GREETINGS[rng(GREETINGS.length, 1)],
    variant: 'info',
  });

  if (totalQ > 0) {
    items.push({
      kind: 'system',
      id: `intro-count-${session.id}`,
      timestamp: baseTs - 1000,
      message: `Нас ждёт ${totalQ} ${pluralQ(totalQ)} — приступим.`,
      variant: 'info',
    });
  }

  // ── Последовательное раскрытие вопросов ─────────────────────────────────────
  // Вопрос N виден если:
  //   - N === 0 (первый всегда виден)
  //   - localDraft[questions[N-1].id] существует (предыдущий отвечен в этом сеансе)
  for (let idx = 0; idx < session.questions.length; idx++) {
    const q = session.questions[idx];
    const qTs = baseTs + idx * 60_000;

    // Проверяем, разрешено ли показывать этот вопрос
    if (idx > 0) {
      const prevQ = session.questions[idx - 1];
      if (!localDraft[prevQ.id]) break; // предыдущий не отвечен → стоп
    }

    items.push({
      kind: 'question',
      id: `question-${q.id}`,
      timestamp: qTs,
      question: q,
      index: idx + 1,
    });

    const draft = localDraft[q.id];
    if (!draft) {
      // Этот вопрос активен и ещё не отвечен — возможно, пользователь печатает
      if (typingText.trim() && (activeQuestionId === q.id || !activeQuestionId)) {
        items.push({
          kind: 'draft_preview',
          id: 'draft-preview-ephemeral',
          timestamp: qTs + 500,
          questionId: q.id,
          text: typingText,
        });
      }
      break; // дальше не показываем пока этот не отвечен
    }

    // Ответ есть — рендерим пузырь
    // isHistorical: если ответа не было в session.currentDraft когда мы начали
    // (localDraft инициализируется из currentDraft при загрузке, поэтому
    //  проверяем через специальный маркер _historical, который проставляется в useDraftSync)
    const isHistorical = !!(draft as DraftAnswer & { _historical?: boolean })._historical;

    items.push({
      kind: 'answer',
      id: `answer-${q.id}`,
      timestamp: qTs + 2000,
      questionId: q.id,
      draft,
      syncStatus: syncStatus[q.id] ?? (isHistorical ? 'synced' : 'pending'),
      isHistorical,
    });
  }

  // ── Эфемерные события (typing-индикатор бота) ────────────────────────────────
  items.push(...ephemeral);

  return items.sort((a, b) => a.timestamp - b.timestamp);
}
