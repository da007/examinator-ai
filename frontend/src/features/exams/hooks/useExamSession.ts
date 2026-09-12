import { useMemo, useCallback, useEffect, useRef, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useLocation } from 'react-router-dom';
import { submitSession } from '@/api/exam';
import { useSessionTransport } from '../transport/useSessionTransport';
import { useDraftSync } from './useDraftSync';
import { useExamPresentation } from '../presentation/useExamPresentation';
import { buildTimeline } from '../domain/timeline';
import {
  interpretInput,
  executeCommand,
  getVisibleCommands,
  type CommandContext,
  type CommandDefinition,
} from '../domain/interpreter';
import {
  sessionStatusToLifecycle,
  type SessionLifecycle,
  type Interaction,
  type StatusInteraction,
} from '../domain/interactions';
import { APP_CONFIG } from '@/config/app';
import type { QuestionShort } from '@/types';
import { notify } from '@/store/useNotificationStore';

export interface UseExamSessionReturn {
  lifecycle: SessionLifecycle;
  timeline: Interaction[];
  questions: QuestionShort[];
  totalQuestions: number;
  activeQuestionId: string | null;
  isSidebarOpen: boolean;
  isBotTyping: boolean;
  isSyncing: boolean;
  lastSyncTime: number | null;
  visibleCommands: CommandDefinition[];
  typingText: string;
  setTypingText: (text: string) => void;
  processInput: (text: string) => boolean;
  submitAnswer: (questionId: string, draft: { text: string; formula?: any }) => void;
  goToQuestion: (id: string) => void;
  goToNext: () => void;
  setBotTyping: (val: boolean) => void;
  submitExam: () => void;
  flushSync: () => Promise<void>;
  isSubmitting: boolean;
  localDraft: Record<string, any>; // для ChatExamView (edit: заполнить поле)
}

export function useExamSession(sessionId: string): UseExamSessionReturn {
  const questionsCache = useRef<QuestionShort[]>([]);
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();

  const { session, isSyncing } = useSessionTransport(sessionId);
  const {
    activeQuestionId,
    isSidebarOpen,
    isBotTyping,
    setActiveQuestion,
    scrollToInteraction,
    setBotTyping,
  } = useExamPresentation();

  const [typingText, setTypingText] = useState('');

  const lifecycle = useMemo(
    () => (session ? sessionStatusToLifecycle(session.status) : 'initializing'),
    [session],
  );

  const questions = useMemo(() => {
    const cur = session?.questions ?? [];
    if (cur.length === 0 && questionsCache.current.length > 0) return questionsCache.current;
    if (cur.length > 0) questionsCache.current = cur;
    return cur;
  }, [session]);

  const { localDraft, syncStatus, updateAnswer, flushSync, lastSyncTime } = useDraftSync({
    sessionId,
    serverVersion: session?.version,
    initialServerDraft: session?.currentDraft,
  });

  const ephemeral: StatusInteraction[] = useMemo(() => {
    if (!isBotTyping) return [];
    return [{
      kind: 'status',
      id: 'ephemeral-typing',
      timestamp: Date.now(),
      label: 'Экзаменатор читает ваш ответ…',
      statusType: 'typing',
    }];
  }, [isBotTyping]);

  const timeline = useMemo(() => {
    if (!session) return [];
    return buildTimeline({ session, localDraft, syncStatus, activeQuestionId, ephemeral, typingText });
  }, [session, localDraft, syncStatus, activeQuestionId, ephemeral, typingText]);

  // ── Навигация ─────────────────────────────────────────────────────────────
  const goToQuestion = useCallback(
    (id: string) => { setActiveQuestion(id); scrollToInteraction(`question-${id}`); },
    [setActiveQuestion, scrollToInteraction],
  );

  const goToNext = useCallback(() => {
    const idx = questions.findIndex((q) => q.id === activeQuestionId);
    const next = questions[idx + 1];
    if (next) goToQuestion(next.id);
  }, [questions, activeQuestionId, goToQuestion]);

  // ── Submit ────────────────────────────────────────────────────────────────
  const submitMutation = useMutation({
    mutationFn: async () => { await flushSync(); return submitSession(sessionId); },
    onSuccess: (updated) => {
      queryClient.setQueryData(['exam-session', sessionId], updated);
      navigate(`/exam/${sessionId}/result`);
    },
    onError: () => notify('error', 'Не удалось сдать экзамен. Попробуйте снова.'),
  });

  // ── Команды ───────────────────────────────────────────────────────────────
  const commandCtx: CommandContext = useMemo(() => {
    const currentIndex = questions.findIndex((q) => q.id === activeQuestionId);
    const isLast = questions.length > 0 && currentIndex === questions.length - 1;
    return {
      isLastQuestion: isLast,
      canEdit: APP_CONFIG.exam.chatMode.allowEditingPastAnswers,
      actions: {
        goToNext,
        submit: () => submitMutation.mutate(),
        editQuestion: (arg) => {
          const num = parseInt(arg, 10);
          if (isNaN(num)) return;
          const target = questions[num - 1];
          if (target) { setActiveQuestion(target.id); setTimeout(() => scrollToInteraction(`question-${target.id}`), 50); }
        },
        showStatus: () => {},
      },
    };
  }, [questions, activeQuestionId, goToNext, submitMutation, setActiveQuestion, scrollToInteraction]);

  const visibleCommands = useMemo(() => getVisibleCommands(commandCtx), [commandCtx]);

  const submitAnswer = useCallback(
    (questionId: string, draft: { text: string; formula?: any }) => updateAnswer(questionId, draft),
    [updateAnswer],
  );

  const processInput = useCallback(
    (rawText: string) => {
      const interpreted = interpretInput(rawText);
      if (interpreted.kind === 'command') return executeCommand(interpreted, commandCtx);
      if (activeQuestionId && interpreted.kind === 'answer') {
        submitAnswer(activeQuestionId, { text: interpreted.text });
        return true;
      }
      return false;
    },
    [activeQuestionId, submitAnswer, commandCtx],
  );

  // ── Инициализация activeQuestionId ────────────────────────────────────────
  // BUG-FIX: раньше эффект срабатывал сразу с пустым localDraft (до инициализации
  // из server-draft), устанавливал activeQuestionId = q0 и больше не перезапускался.
  // При возобновлённой сессии это приводило к тому, что ответы сохранялись
  // не в тот вопрос.
  //
  // FIX: ждём, пока localDraft не будет готов для сессий с существующими ответами,
  // и сбрасываем activeQuestionId на первый неотвеченный вопрос при каждом
  // значимом изменении localDraft (не при правке конкретного ответа).
  const activeInitialized = useRef(false);
  const localDraftSize = Object.keys(localDraft).length;

  useEffect(() => {
    if (!session || questions.length === 0) return;

    const serverDraftSize = Object.keys(session.currentDraft ?? {}).length;
    const hasSavedData = serverDraftSize > 0;

    // Для сессий с данными ждём, пока useDraftSync их проинициализирует
    if (hasSavedData && localDraftSize === 0) return;

    // После инициализации не сбрасываем если уже стоим на неотвеченном вопросе
    if (activeInitialized.current && activeQuestionId && !localDraft[activeQuestionId]) return;

    const firstUnanswered = questions.find((q) => {
      const answer = localDraft[q.id];
      // Считаем вопрос неотвеченным, если ответа нет ВООБЩЕ или текст пустой
      return !answer || !answer.text?.trim();
   });
    const target = firstUnanswered?.id ?? questions[questions.length - 1].id;

    activeInitialized.current = true;
    setActiveQuestion(target);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session, questions, localDraftSize, setActiveQuestion]);
  // Намеренно не включаем activeQuestionId и localDraft (объект) в deps:
  // localDraftSize дает нам триггер при значимых изменениях без лишних пересчётов.

  // ── Редиректы ────────────────────────────────────────────────────────────
  useEffect(() => {
    if (lifecycle === 'processing' || lifecycle === 'completed') {
      const isExamPath =
        location.pathname.includes(`/exam/${sessionId}`) &&
        !location.pathname.includes('/result');
      if (isExamPath) navigate(`/exam/${sessionId}/result`, { replace: true });
    }
  }, [lifecycle, sessionId, navigate, location.pathname]);

  useEffect(() => { return () => { useExamPresentation.getState().reset(); }; }, []);

  return {
    lifecycle, timeline, questions, totalQuestions: questions.length,
    activeQuestionId, isSidebarOpen, isBotTyping, isSyncing, lastSyncTime,
    visibleCommands, typingText, setTypingText,
    processInput, submitAnswer, goToQuestion, goToNext, setBotTyping,
    submitExam: () => submitMutation.mutate(),
    flushSync, isSubmitting: submitMutation.isPending,
    localDraft,
  };
}
