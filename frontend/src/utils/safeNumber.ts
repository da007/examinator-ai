/** Утилиты безопасного форматирования чисел. Защита от NaN / null / undefined. */

/** Доля (0.0–1.0) → "42%". При невалидном значении → "—" */
export function fmtPct(value: number | null | undefined, decimals = 0): string {
  if (value == null || !isFinite(value)) return '—';
  return `${(value * 100).toFixed(decimals)}%`;
}

/** Число → строка с fallback '—' */
export function fmtNum(value: number | null | undefined, decimals = 2): string {
  if (value == null || !isFinite(value)) return '—';
  return value.toFixed(decimals);
}

/** Округление с защитой от None */
export function safeRound(value: number | null | undefined, decimals = 2): number {
  if (value == null || !isFinite(value)) return 0;
  const factor = 10 ** decimals;
  return Math.round(value * factor) / factor;
}
