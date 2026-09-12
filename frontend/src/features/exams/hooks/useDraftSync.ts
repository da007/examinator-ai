// ─── Draft Sync ───────────────────────────────────────────────────────────────
// BUG-FIX история:
//  FIXED: инициализация из server-draft не срабатывала при перезагрузке —
//         useEffect([sessionId]) не перезапускался когда данные наконец приходили.
//         Решение: добавлен флаг hasServerData в зависимости.
//  FIXED: PATCH отправлял только последний ответ, затирая предыдущие.
//         Решение: fullDraftRef хранит полный черновик, шлём его целиком.

import { useState, useCallback, useRef, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { patchDraft } from '@/api/exam';
import { APP_CONFIG } from '@/config/app';
import type { DraftAnswer } from '@/types';
import type { SyncStatus } from '../domain/interactions';

interface UseDraftSyncOptions {
  sessionId: string;
  serverVersion: number | undefined;
  initialServerDraft?: Record<string, DraftAnswer>;
}

interface DraftSyncState {
  localDraft: Record<string, DraftAnswer>;
  syncStatus: Record<string, SyncStatus>;
  updateAnswer: (questionId: string, draft: DraftAnswer) => void;
  flushSync: () => Promise<void>;
  lastSyncTime: number | null;
}

export type HistoricalDraft = DraftAnswer & { _historical: true };

export function markHistorical(draft: DraftAnswer): HistoricalDraft {
  return { ...draft, _historical: true };
}

export function isHistoricalDraft(draft: DraftAnswer): draft is HistoricalDraft {
  return !!(draft as HistoricalDraft)._historical;
}

export function useDraftSync({
  sessionId,
  serverVersion,
  initialServerDraft,
}: UseDraftSyncOptions): DraftSyncState {
  const queryClient = useQueryClient();
  const [localDraft, setLocalDraft] = useState<Record<string, DraftAnswer>>({});
  const [syncStatus, setSyncStatus] = useState<Record<string, SyncStatus>>({});
  const [lastSyncTime, setLastSyncTime] = useState<number | null>(null);

  const debounceRef   = useRef<ReturnType<typeof setTimeout> | null>(null);
  const versionRef    = useRef<number>(serverVersion ?? 0);
  const isInitialized = useRef(false);

  // fullDraftRef — зеркало localDraft в ref.
  // sendPatch всегда читает его целиком → не теряет предыдущие ответы.
  const fullDraftRef = useRef<Record<string, DraftAnswer>>({});

  // ── ИНИЦИАЛИЗАЦИЯ ─────────────────────────────────────────────────────────
  // BUG: раньше зависимость была только [sessionId].
  // При перезагрузке: session=undefined → effect уходит ранним return.
  // Когда session наконец грузится (sessionId не менялся) — effect не перезапускался.
  // FIX: добавляем hasServerData в зависимости — он меняется false→true при загрузке.
  const hasServerData = initialServerDraft !== undefined;

  useEffect(() => {
    if (isInitialized.current) return;
    if (!hasServerData) return;           // данные ещё не пришли с сервера

    isInitialized.current = true;

    const serverDraft = initialServerDraft!;
    const keys = Object.keys(serverDraft);

    if (keys.length === 0) return;        // чистая сессия — инициализировать нечего

    const historical: Record<string, DraftAnswer> = {};
    const statuses: Record<string, SyncStatus> = {};
    for (const qId of keys) {
      historical[qId] = markHistorical(serverDraft[qId]);
      statuses[qId] = 'synced';
    }

    fullDraftRef.current = historical;
    setLocalDraft(historical);
    setSyncStatus(statuses);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, hasServerData]);

  if (serverVersion !== undefined && serverVersion > versionRef.current) {
    versionRef.current = serverVersion;
  }

  // ── MUTATION ──────────────────────────────────────────────────────────────
  const mutation = useMutation({
    mutationFn: ({ draft, version }: { draft: Record<string, DraftAnswer>; version: number }) =>
      patchDraft(sessionId, { version, currentDraft: draft }),

    onSuccess: (updatedSession) => {
      queryClient.setQueryData(['exam-session', sessionId], updatedSession);
      versionRef.current = updatedSession.version;
      setLastSyncTime(Date.now());
      setSyncStatus((prev) => {
        const next = { ...prev };
        for (const id of Object.keys(next)) {
          if (next[id] === 'pending') next[id] = 'synced';
        }
        return next;
      });
    },

    onError: (error: unknown) => {
      const status = (error as { response?: { status?: number } }).response?.status;
      if (status === 409) {
        queryClient.invalidateQueries({ queryKey: ['exam-session', sessionId] });
      }
      setSyncStatus((prev) => {
        const next = { ...prev };
        for (const id of Object.keys(next)) {
          if (next[id] === 'pending') next[id] = 'error';
        }
        return next;
      });
    },
  });

  // ── SEND PATCH: всегда шлём ПОЛНЫЙ черновик ───────────────────────────────
  const sendPatch = useCallback((): Promise<void> => {
    const draft = fullDraftRef.current;
    if (Object.keys(draft).length === 0) return Promise.resolve();
    return mutation.mutateAsync({ draft, version: versionRef.current }).then(() => undefined);
  }, [mutation]);

  // ── UPDATE ANSWER ─────────────────────────────────────────────────────────
  const updateAnswer = useCallback(
    (questionId: string, draft: DraftAnswer) => {
      const cleanDraft = { ...draft } as DraftAnswer & { _historical?: boolean };
      delete cleanDraft._historical;

      // Обновляем ref (для sendPatch) и state (для рендера)
      fullDraftRef.current = { ...fullDraftRef.current, [questionId]: cleanDraft };
      setLocalDraft((prev) => ({ ...prev, [questionId]: cleanDraft }));
      setSyncStatus((prev) => ({ ...prev, [questionId]: 'pending' }));

      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => sendPatch(), APP_CONFIG.exam.autoSaveDebounceMs);
    },
    [sendPatch],
  );

  const flushSync = useCallback((): Promise<void> => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    return sendPatch();
  }, [sendPatch]);

  return { localDraft, syncStatus, updateAnswer, flushSync, lastSyncTime };
}
