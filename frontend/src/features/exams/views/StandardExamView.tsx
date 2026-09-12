import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Menu, ChevronLeft, ChevronRight, CheckCircle2, Cloud, Sigma } from 'lucide-react';
import type { ExamViewProps } from '../presentation/ExamViewContract';
import { useExamPresentation } from '../presentation/useExamPresentation';
import { clsx } from 'clsx';
import type { QuestionShort } from '@/types';  // B-1
import { PageHeader } from '@/components/PageHeader';
import { ConfirmDialog } from '@/components/ConfirmDialog';

export function StandardExamView(props: ExamViewProps) {
  const {
    lifecycle,
    questions,
    totalQuestions,
    activeQuestionId,
    isSidebarOpen,
    isSyncing,
    flushSync,
    goToQuestion,
    submitExam,
    isSubmitting,
    timeline,
    lastSyncTime,
    submitAnswer,
  } = props;

  const { toggleSidebar } = useExamPresentation();
  const navigate = useNavigate();

  // 1. Локальный стейт для мгновенного ввода
  const [text, setText] = useState('');
  const [formula, setFormula] = useState('');
  const [exitDialogOpen, setExitDialogOpen] = useState(false);

  const activeQuestion = questions.find((q: QuestionShort) => q.id === activeQuestionId);
  const activeIndex = questions.findIndex((q: QuestionShort) => q.id === activeQuestionId);

  // 2. СИНХРОНИЗАЦИЯ: Подгружаем существующий ответ при смене вопроса
  useEffect(() => {
    if (activeQuestionId) {
      const existing = timeline.find(
        (i) => i.kind === 'answer' && i.questionId === activeQuestionId
      );
      if (existing && existing.kind === 'answer') {
        setText(existing.draft.text || '');
        setFormula(existing.draft.formula?.latex || '');
      } else {
        setText('');
        setFormula('');
      }
    }
  }, [activeQuestionId, timeline]);

  // 3. ОБРАБОТКА ВВОДА
  const handleChange = (newText: string, newFormula: string) => {
    setText(newText);
    setFormula(newFormula);
    
    if (activeQuestionId) {
      submitAnswer(activeQuestionId, { 
        text: newText, 
        formula: newFormula ? {
          raw: newFormula,
          latex: newFormula,
          normalized: null
        } : undefined
      });
    }
  };

  // 4. НАВИГАЦИЯ: Принудительный сброс буфера (Flush)
  const onNavigate = useCallback((targetId: string) => {
    flushSync(); 
    goToQuestion(targetId);
  }, [flushSync, goToQuestion]);

  const isLast = activeIndex === totalQuestions - 1;
  const isFirst = activeIndex === 0;

  return (
    <div className="std-layout">
      {/* ── HEADER ── */}
      <PageHeader
        title={activeQuestion ? activeQuestion.questionText.slice(0, 40) + '...' : 'Загрузка...'}
        subtitle={`Вопрос ${activeIndex + 1} из ${totalQuestions}`}
        leftAction={
          <button
            onClick={toggleSidebar}
            className={clsx(
              "p-2 -ml-2 rounded-xl transition-all",
              isSidebarOpen ? "bg-primary text-white" : "hover:bg-app text-muted-app"
            )}
            title={isSidebarOpen ? "Скрыть навигацию" : "Открыть навигацию"}
          >
            <Menu size={20} />
          </button>
        }
        actions={
          <div className="flex items-center gap-4">
            <div className={clsx(
              "text-[10px] font-mono flex items-center gap-2 transition-colors",
              isSyncing ? "text-primary" : "text-muted-app"
            )}>
              <Cloud size={14} className={isSyncing ? "animate-pulse" : ""} />
              <span className="hidden sm:inline">
                {isSyncing ? 'СИНХРОНИЗАЦИЯ...' : lastSyncTime ? 'СОХРАНЕНО' : 'БЕЗ ИЗМЕНЕНИЙ'}
              </span>
            </div>
            
            <button 
              className="bg-destructive/10 text-destructive hover:bg-destructive hover:text-white px-3 py-1.5 rounded text-[10px] font-bold transition-all"
              onClick={() => setExitDialogOpen(true)}
            >
              ВЫЙТИ
            </button>
            <button 
              className="std-nav-btn std-nav-btn--primary py-1.5 px-4 text-xs font-bold"
              onClick={async () => { await flushSync(); submitExam(); }}
              disabled={isSubmitting || lifecycle !== 'ready'}
            >
              {isSubmitting ? '...' : 'СДАТЬ РАБОТУ'}
            </button>
          </div>
        }
      />

      <div className="std-body">
        {/* ── SIDEBAR ── */}
        <aside className={clsx("chat-nav", isSidebarOpen && "chat-nav--open")}>
          <div className="chat-nav__header">
            <span className="chat-nav__title">Оглавление</span>
          </div>
          <div className="chat-nav__list">
            {questions.map((q: QuestionShort, idx: number) => {
              const isAnswered = timeline.some(i => 
                i.kind === 'answer' && 
                i.questionId === q.id && 
                (i.draft.text?.trim() || i.draft.formula?.latex?.trim())
              );
              return (
                <button
                  key={q.id}
                  className={clsx(
                    "chat-nav__item",
                    q.id === activeQuestionId && "chat-nav__item--active",
                    isAnswered && "chat-nav__item--answered"
                  )}
                  onClick={() => onNavigate(q.id)}
                >
                  <span className="chat-nav__item-num">{idx + 1}</span>
                  <span className="chat-nav__item-text truncate">{q.questionText}</span>
                  {isAnswered && <CheckCircle2 size={12} className="text-success ml-auto" />}
                </button>
              );
            })}
          </div>
        </aside>

        {/* ── CONTENT AREA ── */}
        <main className="std-main bg-app/50">
          {activeQuestion && (
            <div 
              key={activeQuestion.id} 
              className="std-question-panel bg-surface p-10 border border-app shadow-sm rounded-lg mx-auto max-w-3xl animate-in fade-in slide-in-from-bottom-2 duration-300"
            >
              <div className="std-question-header flex justify-between items-center mb-6">
                <span className="std-question-num uppercase tracking-tighter font-bold opacity-40">
                  Вопрос {activeIndex + 1} / {totalQuestions}
                </span>
                <span className="bg-app px-2 py-1 rounded text-[10px] font-bold uppercase text-primary border border-primary/20">
                  {activeQuestion.difficulty}
                </span>
              </div>

              <h2 className="std-question-text text-2xl font-medium leading-tight mb-10 text-app">
                {activeQuestion.questionText}
              </h2>

              <div className="std-answer-section space-y-8">
                <div className="space-y-3">
                  <label className="text-[10px] font-bold uppercase tracking-widest text-muted-app">Ваш развернутый ответ</label>
                  <textarea
                    className="std-answer-textarea focus:border-primary outline-none transition-all bg-app/30 border-app"
                    placeholder="Начните вводить ответ здесь..."
                    value={text}
                    onChange={(e) => handleChange(e.target.value, formula)}
                  />
                </div>

                {activeQuestion.questionType === 'formula' && (
                  <div className="space-y-3 p-6 bg-primary/[0.02] border border-primary/10 rounded-lg">
                    <label className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-primary">
                      <Sigma size={14} /> Математическая нотация (LaTeX)
                    </label>
                    <input
                      className="std-answer-input font-mono focus:border-primary outline-none transition-all bg-surface border-app"
                      placeholder="\sigma = \sqrt{\frac{1}{N} \sum_{i=1}^{N} (x_i - \mu)^2}"
                      value={formula}
                      onChange={(e) => handleChange(text, e.target.value)}
                    />
                  </div>
                )}
              </div>

              {/* ── НИЖНЯЯ НАВИГАЦИЯ ── */}
              <div className="mt-12 pt-8 border-t border-app flex justify-between items-center">
                <button
                  className="flex items-center gap-2 px-6 py-3 rounded-xl border border-app hover:border-primary hover:text-primary transition-all disabled:opacity-20 text-sm font-medium"
                  disabled={isFirst || !questions[activeIndex - 1]}
                  onClick={() => {
                    const targetId = questions[activeIndex - 1]?.id;
                    if (targetId) onNavigate(targetId);
                  }}
                >
                  <ChevronLeft size={18} /> Предыдущий вопрос
                </button>

                <div className="flex gap-4">
                  {!isLast ? (
                    <button
                      className="flex items-center gap-2 px-8 py-3 rounded-xl bg-primary text-primary-fg hover:bg-primary-hover transition-all font-bold text-sm shadow-lg shadow-primary/20"
                      disabled={!questions[activeIndex + 1]}
                      onClick={() => {
                        const targetId = questions[activeIndex + 1]?.id;
                        if (targetId) onNavigate(targetId);
                      }}
                    >
                      Следующий вопрос <ChevronRight size={18} />
                    </button>
                  ) : (
                    <button
                      className="flex items-center gap-2 px-8 py-3 rounded-xl bg-success text-white hover:opacity-90 transition-all font-bold text-sm shadow-lg shadow-success/20"
                      onClick={async () => { await flushSync(); submitExam(); }}
                      disabled={isSubmitting}
                    >
                      Завершить и отправить <CheckCircle2 size={18} />
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}
        </main>
        <ConfirmDialog
          open={exitDialogOpen}
          title="Выйти из экзамена?"
          description="Прогресс сохранится. Вы сможете вернуться позже."
          confirmLabel="Выйти"
          cancelLabel="Остаться"
          onConfirm={() => navigate('/dashboard')}
          onCancel={() => setExitDialogOpen(false)}
        />
      </div>
    </div>
  );
}