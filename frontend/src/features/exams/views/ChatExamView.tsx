import { useRef, useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Send, Menu, Cloud, Edit2, X, CheckCircle2 } from 'lucide-react';
import type { ExamViewProps } from '../presentation/ExamViewContract';
import { InteractionRenderer } from '../renderers/InteractionRenderer';
import { useExamPresentation } from '../presentation/useExamPresentation';
import { APP_CONFIG } from '@/config/app';
import { clsx } from 'clsx';
import type { QuestionShort } from '@/types';
import { PageHeader } from '@/components/PageHeader';
import { ConfirmDialog } from '@/components/ConfirmDialog';
import { notify } from '@/store/useNotificationStore';

interface EditingInfo {
  questionId: string;
  index: number;
  /** Краткий текст вопроса для метки */
  questionPreview: string;
}

export function ChatExamView(props: ExamViewProps) {
  const {
    lifecycle,
    timeline,
    questions,
    totalQuestions,
    activeQuestionId,
    isSidebarOpen,
    isBotTyping,
    isSyncing,
    processInput,
    goToQuestion,
    setBotTyping,
    submitExam,
    isSubmitting,
    visibleCommands,
    setTypingText: _setTypingText, // не используется — черновик только в поле
    localDraft,
  } = props;

  const { toggleSidebar, scrollTargetId, clearScrollTarget } = useExamPresentation();
  const navigate = useNavigate();

  const [inputValue, setInputValue]     = useState('');
  const [editingInfo, setEditingInfo]   = useState<EditingInfo | null>(null);
  const [exitDialogOpen, setExitDialogOpen]     = useState(false);
  const [submitDialogOpen, setSubmitDialogOpen] = useState(false);

  const feedRef     = useRef<HTMLDivElement>(null);
  const inputRef    = useRef<HTMLTextAreaElement>(null);
  const interactionRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  // ── Скролл ──────────────────────────────────────────────────────────────
  useEffect(() => {
    if (scrollTargetId) {
      const el = interactionRefs.current.get(scrollTargetId);
      if (el) { el.scrollIntoView({ behavior: 'smooth', block: 'center' }); clearScrollTarget(); }
    } else if (feedRef.current) {
      feedRef.current.scrollTo({ top: feedRef.current.scrollHeight, behavior: 'smooth' });
    }
  }, [timeline.length, isBotTyping, scrollTargetId, clearScrollTarget]);

  // ── Сброс editingInfo если вопрос, который редактировался, изменился ───
  useEffect(() => {
    if (editingInfo && activeQuestionId !== editingInfo.questionId) {
      setEditingInfo(null);
    }
  }, [activeQuestionId, editingInfo]);

  // ── ФИХ #1: Восстановление черновика из localStorage при смене вопроса ──
  useEffect(() => {
  if (activeQuestionId) {
    const saved = localStorage.getItem(`chat_draft_${activeQuestionId}`);
    if (saved) {
      setInputValue(saved);
      // Важно: подгоняем высоту textarea под восстановленный текст
      requestAnimationFrame(() => {
        if (inputRef.current) {
          inputRef.current.style.height = 'auto';
          inputRef.current.style.height = `${inputRef.current.scrollHeight}px`;
        }
      });
    } else {
      setInputValue(''); // Очищаем, если черновика нет
    }
  }
}, [activeQuestionId]);

  // ── ФИХ #1: Сохранение черновика в localStorage при каждом вводе ────────
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setInputValue(val);
    
    if (activeQuestionId) {
      // Сохраняем локально (мгновенно)
      localStorage.setItem(`chat_draft_${activeQuestionId}`, val);
      
      // Отправляем в хук для фоновой синхронизации с бэкендом (Debounced)
      // Теперь препод увидит текст в реальном времени!
      props.submitAnswer(activeQuestionId, { text: val });
    }

    // Ресайз поля
    e.target.style.height = 'auto';
    e.target.style.height = `${e.target.scrollHeight}px`;
  };

  // ── Отправка ────────────────────────────────────────────────────────────
  const onSend = useCallback((textOverride?: string) => {
    const text = (textOverride ?? inputValue).trim();
    if (!text || isBotTyping || lifecycle !== 'ready') return;

    const wasCommand = processInput(text);

    if (!wasCommand && activeQuestionId) {
      // ── ФИХ #1: Очищаем черновик из localStorage после отправки ────────
      localStorage.removeItem(`draft_input_${activeQuestionId}`);

      if (!textOverride) {
        setInputValue('');
        if (inputRef.current) inputRef.current.style.height = 'auto';
      }
      setEditingInfo(null);

      setBotTyping(true);

      // ── ФИХ #3: После ответа переходим к ближайшему неотвеченному вопросу,
      //    а не тупо к следующему по индексу. Это корректно работает при
      //    редактировании уже отвеченных вопросов. ──────────────────────────
      setTimeout(() => {
        setBotTyping(false);

        // Ищем первый вопрос без ответа (исключая только что отвеченный)
        const nextUnanswered = questions.find(
          (q) => !localDraft[q.id] && q.id !== activeQuestionId,
        );

        if (nextUnanswered) {
          goToQuestion(nextUnanswered.id);
        } else {
          // Все вопросы отвечены — переходим к последнему (для финального ревью)
          const lastQ = questions[questions.length - 1];
          if (lastQ && activeQuestionId !== lastQ.id) {
            goToQuestion(lastQ.id);
          }
        }
      }, 1200);
    }

    if (!textOverride) {
      setInputValue('');
      if (inputRef.current) inputRef.current.style.height = 'auto';
    }
    setTimeout(() => inputRef.current?.focus(), 10);
  }, [
    inputValue, isBotTyping, lifecycle, processInput,
    activeQuestionId, questions, localDraft, setBotTyping, goToQuestion,
  ]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); onSend(); }
    if (e.key === 'Escape' && editingInfo) { setEditingInfo(null); setInputValue(''); }
  };

  // ── Обработчик кнопки «Редактировать» ────────────────────────────────────
  const handleEdit = useCallback((qId: string) => {
    const qIndex  = questions.findIndex((q) => q.id === qId);
    const question = questions[qIndex];
    if (!question) return;

    // Получаем текущий ответ из localDraft
    const existingDraft = localDraft[qId] as (typeof localDraft[string] & { _historical?: boolean }) | undefined;
    const existingText  = existingDraft?.text ?? '';

    // Переключаем активный вопрос
    goToQuestion(qId);

    // Заполняем поле и выставляем метку
    setInputValue(existingText);
    setEditingInfo({
      questionId: qId,
      index: qIndex + 1,
      questionPreview: question.questionText.length > 55
        ? question.questionText.slice(0, 52) + '…'
        : question.questionText,
    });

    // Авторесайз textarea
    requestAnimationFrame(() => {
      if (inputRef.current) {
        inputRef.current.style.height = 'auto';
        inputRef.current.style.height = `${inputRef.current.scrollHeight}px`;
        inputRef.current.focus();
        // Ставим курсор в конец текста
        const len = inputRef.current.value.length;
        inputRef.current.setSelectionRange(len, len);
      }
    });
  }, [questions, localDraft, goToQuestion]);

  const cancelEdit = () => {
    setEditingInfo(null);
    setInputValue('');
    if (activeQuestionId) {
      localStorage.removeItem(`draft_input_${activeQuestionId}`);
    }
  };

  // ── Прогресс ─────────────────────────────────────────────────────────────
  const answeredCount = questions.filter((q: QuestionShort) =>
    timeline.some((i) => i.kind === 'answer' && (i as any).questionId === q.id),
  ).length;
  const progressPct = totalQuestions > 0 ? (answeredCount / totalQuestions) * 100 : 0;

  const handleGoToQuestion = useCallback((targetId: string) => {
    const currentIdx = questions.findIndex((q: QuestionShort) => q.id === activeQuestionId);
    const targetIdx  = questions.findIndex((q: QuestionShort) => q.id === targetId);
    const isAnswered = (qId: string) =>
      timeline.some((i) => i.kind === 'answer' && (i as any).questionId === qId);

    if (targetIdx > currentIdx && activeQuestionId && !isAnswered(activeQuestionId)) {
      notify('warning', 'Пожалуйста, ответьте на текущий вопрос прежде чем двигаться дальше');
      return;
    }
    goToQuestion(targetId);
  }, [questions, activeQuestionId, timeline, goToQuestion]);

  const inputDisabled = isBotTyping || lifecycle !== 'ready';

  // ── ФИХ #4: Определяем, является ли активный вопрос математическим ──────
  const activeQuestion = questions.find((q: QuestionShort) => q.id === activeQuestionId);
  const isFormulaQuestion = activeQuestion?.questionType === 'formula';

  return (
    <div className="chat-layout h-screen flex flex-col overflow-hidden bg-app">

      {/* ── HEADER ── */}
      <PageHeader
        title={APP_CONFIG.appName}
        subtitle={`Прогресс: ${answeredCount} из ${totalQuestions}`}
        leftAction={
          <button
            onClick={toggleSidebar}
            className={clsx('p-2 -ml-2 rounded-xl transition-all',
              isSidebarOpen ? 'bg-primary text-white' : 'hover:bg-app text-muted-app')}
            title="Навигация"
          >
            <Menu size={20} />
          </button>
        }
        actions={
          <div className="flex items-center gap-4">
            <div className={clsx('flex items-center gap-2 text-[10px] font-mono transition-opacity',
              isSyncing ? 'opacity-100 text-primary' : 'opacity-40')}>
              <Cloud size={14} className={isSyncing ? 'animate-pulse' : ''} />
              <span className="hidden sm:inline">{isSyncing ? 'Сохранение…' : 'Сохранено'}</span>
            </div>
            <div className="hidden md:block w-32 h-1.5 bg-surface-alt rounded-full overflow-hidden border border-app">
              <div className="h-full bg-primary transition-all duration-500" style={{ width: `${progressPct}%` }} />
            </div>
            <button
              className="bg-destructive/10 text-destructive hover:bg-destructive hover:text-white px-3 py-1.5 rounded text-[10px] font-bold transition-all"
              onClick={() => setExitDialogOpen(true)}
            >
              ВЫЙТИ
            </button>
          </div>
        }
      />

      <div className="chat-body flex flex-1 overflow-hidden">

        {/* ── SIDEBAR ── */}
        <aside className={clsx('chat-nav', isSidebarOpen && 'chat-nav--open')}>
          <div className="chat-nav__header">
            <span className="chat-nav__title">Экзаменационная панель</span>
          </div>

          <div className="chat-nav__list flex-1 overflow-y-auto custom-scrollbar">
            <div className="px-5 py-2">
              <span className="text-[9px] font-black uppercase tracking-[0.2em] text-muted-app">Вопросы</span>
            </div>
            {(() => {
              const activeIdx = questions.findIndex((q: QuestionShort) => q.id === activeQuestionId);
              return questions.map((q: QuestionShort, idx: number) => {
                const isAnswered = timeline.some(
                  (i) => i.kind === 'answer' && (i as any).questionId === q.id &&
                    ((i as any).draft?.text?.trim() || (i as any).draft?.formula?.latex?.trim()),
                );
                const isActive   = q.id === activeQuestionId;
                const isRevealed = idx <= activeIdx;

                if (!isRevealed) {
                  return (
                    <div key={q.id} className="chat-nav__item opacity-30 cursor-not-allowed select-none">
                      <span className="chat-nav__item-num">{idx + 1}</span>
                      <span className="chat-nav__item-text truncate text-muted-app italic">Следующий вопрос</span>
                    </div>
                  );
                }
                return (
                  <button
                    key={q.id}
                    className={clsx('chat-nav__item',
                      isActive && 'chat-nav__item--active',
                      isAnswered && 'chat-nav__item--answered')}
                    onClick={() => handleGoToQuestion(q.id)}
                  >
                    <span className="chat-nav__item-num">{idx + 1}</span>
                    <span className="chat-nav__item-text truncate">{q.questionText}</span>
                    {isAnswered && <CheckCircle2 size={12} className="text-success ml-auto shrink-0" />}
                  </button>
                );
              });
            })()}
          </div>

          <div className="chat-nav__footer p-4 border-t border-app bg-surface">
            <button
              className="w-full py-3 bg-primary text-primary-fg rounded-xl font-bold text-sm shadow-lg shadow-primary/20 disabled:opacity-50 hover:bg-primary-hover transition-all"
              disabled={isSubmitting || lifecycle !== 'ready'}
              onClick={() => setSubmitDialogOpen(true)}
            >
              {isSubmitting ? 'Завершение...' : 'Завершить экзамен'}
            </button>
          </div>
        </aside>

        {/* ── CHAT FEED ── */}
        <main className="chat-feed-wrap flex flex-col flex-1 bg-app/50 relative">
          <div className="chat-feed flex-1 overflow-y-auto" ref={feedRef}>
            <div className="chat-feed__inner max-w-3xl mx-auto p-4 sm:p-8 space-y-4">
              {timeline.map((interaction) => (
                <div
                  key={interaction.id}
                  className="chat-feed__item"
                  ref={(el) => {
                    if (el) interactionRefs.current.set(interaction.id, el);
                    else interactionRefs.current.delete(interaction.id);
                  }}
                >
                  <InteractionRenderer
                    interaction={interaction}
                    onEdit={handleEdit}
                  />
                </div>
              ))}

              {isBotTyping && (
                <div className="flex items-center gap-2 text-muted-app animate-pulse ml-4">
                  <div className="flex gap-1">
                    <span className="w-1.5 h-1.5 bg-current rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-1.5 h-1.5 bg-current rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-1.5 h-1.5 bg-current rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                  <span className="text-[10px] font-bold uppercase tracking-widest">ИИ читает ответ</span>
                </div>
              )}
            </div>
          </div>

          {/* ── INPUT AREA ── */}
          <footer className="chat-input-area bg-surface border-t border-app p-4 sm:p-6">
            <div className="max-w-3xl mx-auto">

              {/* Чипы команд */}
              {visibleCommands.length > 0 && (
                <div className="chat-chips mb-4 flex flex-wrap gap-2">
                  {visibleCommands.map((cmd) => (
                    <button
                      key={cmd.command}
                      className="chat-chip flex items-center gap-2 px-3 py-1.5 rounded-full border border-app hover:border-primary hover:text-primary text-[11px] font-bold transition-all disabled:opacity-30 bg-app/30"
                      onClick={() => onSend(cmd.command)}
                      disabled={inputDisabled}
                    >
                      <cmd.icon size={14} />
                      {cmd.label}
                    </button>
                  ))}
                </div>
              )}

              {/* Метка редактирования */}
              {editingInfo && (
                <div className="flex items-start gap-2 mb-3 px-1 py-2 bg-primary/8 border border-primary/20 rounded-xl">
                  <Edit2 size={12} className="text-primary mt-0.5 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <span className="text-[10px] font-black uppercase tracking-widest text-primary">
                      Редактирование вопроса {editingInfo.index}
                    </span>
                    <p className="text-[11px] text-muted-app mt-0.5 truncate">
                      {editingInfo.questionPreview}
                    </p>
                  </div>
                  <button
                    onClick={cancelEdit}
                    className="text-muted-app hover:text-destructive transition-colors shrink-0 p-1 rounded"
                    title="Отмена"
                  >
                    <X size={13} />
                  </button>
                </div>
              )}

              {/* ── ФИХ #4: Подсказка для математических вопросов ─────────────────
                  Если активный вопрос требует формулу, показываем информер с
                  инструкцией по LaTeX-синтаксису прямо над полем ввода.        */}
              {isFormulaQuestion && (
                <div className="mb-2 p-3 bg-primary/5 border border-primary/20 rounded-xl">
                  <span className="text-[10px] uppercase font-black text-primary mb-1 block tracking-widest">
                    Математический вопрос
                  </span>
                  <p className="text-[11px] text-muted-app leading-relaxed">
                    Оберните формулу в символы <code className="bg-primary/10 text-primary px-1 rounded">$$...$$</code>,
                    например:&nbsp;
                    <code className="bg-primary/10 text-primary px-1 rounded">$$ x^2 + y^2 = z^2 $$</code>&nbsp;
                    — движок автоматически передаст её в математический процессор.
                  </p>
                </div>
              )}

              {/* Поле ввода */}
              <div className="chat-input-row flex items-end gap-3 bg-app/50 border border-app p-2 rounded-2xl focus-within:border-primary/50 focus-within:bg-surface transition-all">
                <textarea
                  ref={inputRef}
                  className="chat-input flex-1 bg-transparent border-none focus:ring-0 text-sm py-2 px-3 resize-none max-h-32 outline-none"
                  rows={1}
                  placeholder={
                    isBotTyping
                      ? 'Подождите, экзаменатор читает ответ…'
                      : isFormulaQuestion
                        ? 'Напишите ответ, формулу оберните в $$ ... $$'
                        : 'Напишите ответ или команду...'
                  }
                  value={inputValue}
                  onChange={handleInputChange}
                  onKeyDown={handleKeyDown}
                  disabled={inputDisabled}
                />
                <button
                  className="chat-send-btn bg-primary text-white p-3 rounded-xl disabled:opacity-20 hover:bg-primary-hover transition-all shadow-lg shadow-primary/20"
                  onClick={() => onSend()}
                  disabled={!inputValue.trim() || inputDisabled}
                >
                  <Send size={18} />
                </button>
              </div>

              {inputValue.length > 0 && (
                <p className="text-[9px] text-muted-app/40 mt-2 text-center">
                  Enter — отправить · Shift+Enter — новая строка · Esc — отмена правки
                </p>
              )}
            </div>
          </footer>
        </main>
      </div>

      <ConfirmDialog
        open={exitDialogOpen}
        title="Выйти из экзамена?"
        description="Прогресс сохранится. Вы сможете вернуться позже."
        confirmLabel="Выйти"
        cancelLabel="Остаться"
        onConfirm={() => navigate('/dashboard')}
        onCancel={() => setExitDialogOpen(false)}
      />
      <ConfirmDialog
        open={submitDialogOpen}
        title="Сдать экзамен?"
        description={`Вы ответили на ${answeredCount} из ${totalQuestions} вопросов.`}
        confirmLabel="Сдать работу"
        cancelLabel="Отмена"
        confirmVariant="primary"
        onConfirm={() => { setSubmitDialogOpen(false); submitExam(); }}
        onCancel={() => setSubmitDialogOpen(false)}
      />
    </div>
  );
}