// ─── DraftPreviewBubble ───────────────────────────────────────────────────────
// Эфемерный пузырь: показывает текст, который студент набирает
// но ещё не отправил. Исчезает после отправки ответа.

import type { DraftPreviewInteraction } from '../domain/interactions';

interface Props {
  interaction: DraftPreviewInteraction;
}

export function DraftPreviewBubble({ interaction }: Props) {
  const words = interaction.text.trim().split(/\s+/);
  // Показываем не более 80 символов чтобы не занимать много места
  const preview = interaction.text.length > 80
    ? interaction.text.slice(0, 77) + '…'
    : interaction.text;

  return (
    <div className="flex flex-col items-end mb-2 animate-in fade-in duration-150">
      <div
        className="max-w-[75%] rounded-2xl rounded-br-sm px-5 py-3 shadow-sm
          bg-primary/20 border border-primary/30 backdrop-blur-sm
          text-app text-sm opacity-70"
        aria-label="Черновик ответа"
      >
        <p className="whitespace-pre-wrap leading-relaxed">{preview}</p>

        {/* Анимированный курсор */}
        <span
          className="inline-block w-0.5 h-4 bg-primary ml-1 align-middle
            animate-[blink_1s_step-end_infinite]"
          aria-hidden="true"
        />
      </div>

      <span className="text-[9px] text-muted-app/50 mt-1 mr-1 uppercase tracking-wider font-bold">
        Черновик · {words.length} {words.length === 1 ? 'слово' : words.length < 5 ? 'слова' : 'слов'}
      </span>
    </div>
  );
}
