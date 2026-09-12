// ─── Examinator AI — Global App Config ───────────────────────────────────────
// Все флаги и константы в одном месте. Менять здесь, не охотиться по компонентам.

export const APP_CONFIG = {
  appName: 'Examinator AI',
  apiBaseUrl: import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1',

  exam: {
    /** Debounce перед отправкой PATCH /draft (мс) */
    autoSaveDebounceMs: 1200,

    /** Polling при статусе 'processing' (мс) */
    pollingIntervalMs: 3000,

    chatMode: {
      /**
       * true  — студент может написать /edit 1 и изменить старый ответ.
       * false — ответил = пузырь визуально заморожен (readonly).
       * Бэкенд ВСЕГДА позволяет редактировать draft до submit,
       * это только UX-ограничение.
       */
      allowEditingPastAnswers: false,

      /** Задержка "печати бота" для реалистичности (мс) */
      typingDelayMs: 600,

      commands: {
        next:   '/next',
        submit: '/submit',
        edit:   '/edit',   // активен только если allowEditingPastAnswers = true
        status: '/status',
      },
    },
  },

  /** Polling после submit — ждём grade_exam_session_task */
  gradingPollingIntervalMs: 3000,
} as const;
