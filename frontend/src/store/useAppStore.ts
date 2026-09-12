import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { AuthUser } from '@/types';

// ── ТИПЫ ──────────────────────────────────────────────────────────────────────

export type Theme = 'light' | 'dark' | 'system';
export type ExamViewMode = 'standard' | 'chat';

interface AuthSlice {
  user: AuthUser | null;
  isAuthenticated: boolean;
  setUser: (user: AuthUser) => void;
  logout: () => void;
}

interface SettingsSlice {
  theme: Theme;
  examViewMode: ExamViewMode;
  setTheme: (theme: Theme) => void;
  setExamViewMode: (mode: ExamViewMode) => void;
  sidebarCollapsed: boolean;
setSidebarCollapsed: (val: boolean) => void;
}

type AppState = AuthSlice & SettingsSlice;

// ── STORE ─────────────────────────────────────────────────────────────────────

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      // ── Auth (НЕ ПЕРСИСТИТСЯ) ──────────────────────────────────────────────
      user: null,
      isAuthenticated: false,

	  sidebarCollapsed: false,
	  setSidebarCollapsed: (sidebarCollapsed) => set({ sidebarCollapsed }),

      setUser: (user) => set({ 
        user, 
        isAuthenticated: true 
      }),

      logout: () => {
        localStorage.removeItem('access_token');
        set({ user: null, isAuthenticated: false });
      },

      // ── Settings (ПЕРСИСТИТСЯ) ─────────────────────────────────────────────
      theme: 'system',
      examViewMode: 'chat', // По умолчанию — чат (основная фишка)

      setTheme: (theme) => set({ theme }),
      setExamViewMode: (mode) => set({ examViewMode: mode }),
    }),
    {
      name: 'app-settings',
      /**
       * ВАЖНО: Мы сохраняем в localStorage только настройки интерфейса.
       * Данные пользователя и флаг авторизации удалены из partialize.
       * Это предотвращает "мигание" интерфейса и обеспечивает безопасность:
       * при обновлении страницы isAuthenticated будет false, пока initAuth в App.tsx
       * не подтвердит валидность токена.
       */
      partialize: (state) => ({
		  theme: state.theme,
		  examViewMode: state.examViewMode,
		  sidebarCollapsed: state.sidebarCollapsed, // <--- Добавить это
		}),
    },
  ),
);

// ── SELECTORS (Shortcut-хуки) ────────────────────────────────────────────────

export const useCurrentUser = () => useAppStore((s) => s.user);
export const useIsAuthenticated = () => useAppStore((s) => s.isAuthenticated);
export const useTheme = () => useAppStore((s) => s.theme);
export const useExamViewMode = () => useAppStore((s) => s.examViewMode);