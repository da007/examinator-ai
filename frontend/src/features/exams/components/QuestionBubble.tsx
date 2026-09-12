// ─── QuestionBubble ───────────────────────────────────────────────────────────
// Пузырь "от системы" — вопрос экзаменатора.
// Левая сторона, строгий академический стиль.
// index передаётся из timeline для отображения порядкового номера.

import type { QuestionInteraction } from '../domain/interactions';
import { MathRenderer } from '@/components/MathRenderer';

interface Props {
  interaction: QuestionInteraction;
}

const DIFFICULTY_LABEL: Record<string, string> = {
  easy:   'Базовый',
  medium: 'Средний',
  hard:   'Сложный',
};

export function QuestionBubble({ interaction }: Props) {
  const { question, index } = interaction;
  const diffLabel = DIFFICULTY_LABEL[question.difficulty] ?? question.difficulty;

  return (
    <div className="exam-bubble exam-bubble--system group">
      {/* Заголовок вопроса */}
      <div className="exam-bubble__meta">
        <span className="exam-bubble__index">Вопрос {index}</span>
        <span className="exam-bubble__tag">{diffLabel}</span>
        {question.questionType === 'formula' && (
          <span className="exam-bubble__tag exam-bubble__tag--formula">∑ Формула</span>
        )}
      </div>

      {/* Текст вопроса */}
      <div className="exam-bubble__text">
        {question.questionType === 'formula' ? (
          <MathRenderer formula={question.questionText} displayMode={true} />
        ) : (
          <p>{question.questionText}</p>
        )}
      </div>
    </div>
  );
}
