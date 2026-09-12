import { Check, Loader2, AlertCircle, Sigma, Edit2, History } from 'lucide-react';
import type { AnswerInteraction } from '../domain/interactions';
import { MathRenderer } from '@/components/MathRenderer';
import { clsx } from 'clsx';

interface Props {
  interaction: AnswerInteraction;
  onEdit?: (questionId: string) => void;
}

export function AnswerBubble({ interaction, onEdit }: Props) {
  const { draft, syncStatus, isHistorical } = interaction;

  return (
    <div className="flex flex-col items-end mb-6 group animate-in fade-in slide-in-from-right-4 duration-300">
      <div className="exam-bubble exam-bubble--user shadow-sm relative">

        {/* Кнопка редактирования */}
        {onEdit && (
          <button
            onClick={() => onEdit(interaction.questionId)}
            className="absolute -left-10 top-1 p-2 text-muted-app hover:text-primary
              opacity-0 group-hover:opacity-100 transition-all"
            title="Редактировать ответ"
          >
            <Edit2 size={16} />
          </button>
        )}

        {/* Текст ответа */}
        {draft.text && (
          <p className="exam-bubble__text whitespace-pre-wrap">{draft.text}</p>
        )}

        {/* Блок LaTeX формулы */}
        {draft.formula?.latex && (
          <div className="exam-bubble__formula mt-3 bg-black/10 rounded border border-white/10 p-3 overflow-x-auto">
            <div className="flex items-center gap-2 mb-2 opacity-70">
              <Sigma size={12} />
              <span className="text-[10px] uppercase font-bold tracking-wider text-white">
                Математическая нотация
              </span>
            </div>
            <div className="text-white">
              <MathRenderer formula={draft.formula.latex} displayMode={true} />
            </div>
          </div>
        )}

        {/* Индикатор синхронизации */}
        <div className={clsx(
          'exam-bubble__sync mt-2 flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-tight transition-all',
          syncStatus === 'synced' && 'text-white/70',
          syncStatus === 'pending' && 'text-white/50 animate-pulse',
          syncStatus === 'error' && 'text-destructive-fg bg-destructive/20 px-1.5 py-0.5 rounded',
        )}>
          {syncStatus === 'synced' && !isHistorical && (
            <><Check size={12} strokeWidth={3} /><span>Сохранено</span></>
          )}
          {syncStatus === 'synced' && isHistorical && (
            <><History size={12} /><span>Загружено из прошлой сессии</span></>
          )}
          {syncStatus === 'pending' && (
            <><Loader2 size={12} className="animate-spin" /><span>Сохранение...</span></>
          )}
          {syncStatus === 'error' && (
            <><AlertCircle size={12} /><span>Ошибка сети</span></>
          )}
        </div>
      </div>
    </div>
  );
}
