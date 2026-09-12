// ─── SystemMessage ────────────────────────────────────────────────────────────

import type { SystemInteraction, StatusInteraction } from '../domain/interactions';

// ── SystemMessage ─────────────────────────────────────────────────────────────

interface SystemProps {
  interaction: SystemInteraction;
}

const VARIANT_CLASSES: Record<NonNullable<SystemInteraction['variant']>, string> = {
  info:    'exam-system--info',
  success: 'exam-system--success',
  warning: 'exam-system--warning',
  error:   'exam-system--error',
};

export function SystemMessage({ interaction }: SystemProps) {
  const variantClass = VARIANT_CLASSES[interaction.variant ?? 'info'];

  return (
    <div className={`exam-system ${variantClass}`}>
      <span className="exam-system__line" aria-hidden="true" />
      <p className="exam-system__text">{interaction.message}</p>
      <span className="exam-system__line" aria-hidden="true" />
    </div>
  );
}

// ── StatusIndicator (typing / saving) ─────────────────────────────────────────

interface StatusProps {
  interaction: StatusInteraction;
}

export function StatusIndicator({ interaction }: StatusProps) {
  if (interaction.statusType === 'typing') {
    return (
      <div className="exam-bubble exam-bubble--system exam-bubble--typing" aria-live="polite">
        <span className="typing-dot" />
        <span className="typing-dot" />
        <span className="typing-dot" />
      </div>
    );
  }

  return (
    <div className="exam-status" aria-live="polite">
      <span className="exam-status__spinner" aria-hidden="true" />
      <span className="exam-status__label">{interaction.label}</span>
    </div>
  );
}
