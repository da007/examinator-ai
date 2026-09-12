import { create } from 'zustand';

const EXAM_SIDEBAR_KEY = 'exam_sidebar_open';

interface ExamPresentationState {
  activeQuestionId: string | null;
  scrollTargetId: string | null;
  isSidebarOpen: boolean;
  isBotTyping: boolean;

  setActiveQuestion: (id: string | null) => void;
  scrollToInteraction: (id: string) => void;
  clearScrollTarget: () => void;
  toggleSidebar: () => void;
  setBotTyping: (typing: boolean) => void;
  reset: () => void;
}

const getSavedSidebarState = (): boolean => {
  try { return localStorage.getItem(EXAM_SIDEBAR_KEY) !== 'false'; } catch { return true; }
};

export const useExamPresentation = create<ExamPresentationState>((set) => ({
  activeQuestionId: null,
  scrollTargetId: null,
  isSidebarOpen: getSavedSidebarState(),
  isBotTyping: false,

  setActiveQuestion: (id) => set({ activeQuestionId: id }),
  scrollToInteraction: (id) => set({ scrollTargetId: id }),
  clearScrollTarget: () => set({ scrollTargetId: null }),
  toggleSidebar: () => set((s) => {
    const next = !s.isSidebarOpen;
    try { localStorage.setItem(EXAM_SIDEBAR_KEY, String(next)); } catch {}
    return { isSidebarOpen: next };
  }),
  setBotTyping: (typing) => set({ isBotTyping: typing }),
  reset: () => set({ activeQuestionId: null, isBotTyping: false, scrollTargetId: null, isSidebarOpen: false }),
}));