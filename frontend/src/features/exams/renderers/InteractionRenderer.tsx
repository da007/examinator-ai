import type {
  Interaction,
  QuestionInteraction,
  AnswerInteraction,
  SystemInteraction,
  StatusInteraction,
  EventInteraction,
  DraftPreviewInteraction,
} from '../domain/interactions';
import { QuestionBubble } from '../components/QuestionBubble';
import { AnswerBubble } from '../components/AnswerBubble';
import { DraftPreviewBubble } from '../components/DraftPreviewBubble';
import { SystemMessage, StatusIndicator } from '../components/SystemMessage';
import { EventRenderer } from './EventRenderer';

interface InteractionRendererProps {
  interaction: Interaction;
  onEdit?: (questionId: string) => void;
}

export function InteractionRenderer({ interaction, onEdit }: InteractionRendererProps) {
  switch (interaction.kind) {
    case 'question':
      return (
        <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
          <QuestionBubble interaction={interaction as QuestionInteraction} />
        </div>
      );

    case 'answer':
      return (
        <div className="animate-in fade-in slide-in-from-right-4 duration-300">
          <AnswerBubble
            interaction={interaction as AnswerInteraction}
            onEdit={onEdit}
          />
        </div>
      );

    case 'draft_preview':
      return (
        <DraftPreviewBubble interaction={interaction as DraftPreviewInteraction} />
      );

    case 'system':
      return (
        <div className="animate-in fade-in duration-500">
          <SystemMessage interaction={interaction as SystemInteraction} />
        </div>
      );

    case 'status':
      return (
        <div className="animate-in fade-in duration-200">
          <StatusIndicator interaction={interaction as StatusInteraction} />
        </div>
      );

    case 'event':
      return (
        <div className="animate-in fade-in duration-300">
          <EventRenderer interaction={interaction as EventInteraction} />
        </div>
      );

    default:
      if (import.meta.env.DEV) {
        console.error(`[InteractionRenderer] Unknown kind:`, (interaction as any).kind);
      }
      return null;
  }
}
