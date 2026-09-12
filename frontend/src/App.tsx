import { useEffect, useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useThemeApplier, useSystemThemeWatcher } from '@/hooks/useThemeApplier';
import { useAppStore, useCurrentUser } from '@/store/useAppStore';
import { getMe } from '@/api/auth';
import { Toaster } from '@/components/Toaster';

// Layouts
import { MainLayout } from '@/layouts/MainLayout';

// Pages
import { LoginPage } from '@/pages/LoginPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { ExamPage } from '@/pages/ExamPage';
import { ExamResultPage } from '@/pages/ExamResultPage';
import { SettingsPage } from '@/pages/SettingsPage';
import { LecturesPage } from '@/pages/LecturesPage';

// Teacher pages
import { TeacherDashboard } from '@/pages/teacher/TeacherDashboard';
import { UploadPage } from '@/pages/teacher/UploadPage';
import { ModerationPage } from '@/pages/teacher/ModerationPage';
import { AnalyticsPage } from '@/pages/teacher/AnalyticsPage';
import { AppealsPage } from '@/pages/teacher/AppealsPage';
import { TeacherLecturesPage } from '@/pages/teacher/TeacherLecturesPage';
import { TeacherPendingReviewsPage } from '@/pages/teacher/TeacherPendingReviewsPage';

// Components
import { ProtectedRoute } from '@/components/ProtectedRoute';

export default function App() {
  useThemeApplier();
  useSystemThemeWatcher();

  const { isAuthenticated} = useAppStore();
  const user = useCurrentUser();
  const [isInitializing, setIsInitializing] = useState(true);

  // Первичная проверка сессии при загрузке вкладки
  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem('access_token');
      if (!token) { setIsInitializing(false); return; }
      try {
        const userData = await getMe();
        useAppStore.getState().setUser(userData);
      } catch (error) {
        console.error('Auth check failed:', error);
        useAppStore.getState().logout();
      } finally {
        setIsInitializing(false);
      }
    };
    initAuth();
  }, []); // E-1: было [setUser, logout] — риск повтора при HMR

  if (isInitializing) {
    return (
      <div className="flex h-screen items-center justify-center bg-app text-app">
        <div className="flex flex-col items-center gap-4">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          <p className="text-sm font-medium opacity-50">Инициализация системы...</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <Routes>
        {/* 1. Публичные маршруты */}
        <Route
          path="/login"
          element={!isAuthenticated ? <LoginPage /> : <Navigate to="/" replace />}
        />

        {/* 2. Изолированные полноэкранные маршруты (без сайдбара) */}
        <Route
          path="/exam/:sessionId"
          element={
            <ProtectedRoute>
              <ExamPage />
            </ProtectedRoute>
          }
        />

        {/* 3. Платформенные маршруты (с MainLayout / Sidebar) */}
        <Route element={<MainLayout />}>
          {/* Корень: редирект в зависимости от роли */}
          <Route
            path="/"
            element={
              !user ? (
                <Navigate to="/login" replace />
              ) : user.role === 'student' ? (
                <Navigate to="/dashboard" replace />
              ) : (
                <Navigate to="/teacher/dashboard" replace />
              )
            }
          />

          {/* Дашборд студента */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute allowedRoles={['student', 'admin']}>
                <DashboardPage />
              </ProtectedRoute>
            }
          />

          {/* Общие страницы */}
          <Route path="/settings" element={<SettingsPage />} />

          {/* Результат экзамена */}
          <Route
            path="/exam/:sessionId/result"
            element={
              <ProtectedRoute allowedRoles={['student', 'admin', 'teacher', 'ta']}>
                <ExamResultPage />
              </ProtectedRoute>
            }
          />

          {/* Мои лекции (студент) */}
          <Route
            path="/lectures"
            element={
              <ProtectedRoute allowedRoles={['student', 'admin']}>
                <LecturesPage />
              </ProtectedRoute>
            }
          />

          {/* Страницы преподавателя */}
          <Route path="/teacher">
            <Route
              path="dashboard"
              element={
                <ProtectedRoute allowedRoles={['teacher', 'admin', 'ta']}>
                  <TeacherDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="lectures"
              element={
                <ProtectedRoute allowedRoles={['teacher', 'admin']}>
                  <TeacherLecturesPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="reviews"
              element={
                <ProtectedRoute allowedRoles={['teacher', 'admin', 'ta']}>
                  <TeacherPendingReviewsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="upload"
              element={
                <ProtectedRoute allowedRoles={['teacher', 'admin']}>
                  <UploadPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="moderation/:lectureId"
              element={
                <ProtectedRoute allowedRoles={['teacher', 'admin']}>
                  <ModerationPage />
                </ProtectedRoute>
              }
            />
            {/*
              ИСПРАВЛЕНО: маршрут аналитики теперь принимает :lectureId.
              Без него AnalyticsPage получала undefined из useParams и не загружала данные.
              Навигация из TeacherLecturesPage: navigate(`/teacher/analytics/${lecture.id}`)
            */}
            <Route
              path="analytics/:lectureId"
              element={
                <ProtectedRoute allowedRoles={['teacher', 'admin']}>
                  <AnalyticsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="appeals"
              element={
                <ProtectedRoute allowedRoles={['teacher', 'admin', 'ta']}>
                  <AppealsPage />
                </ProtectedRoute>
              }
            />
          </Route>
        </Route>

        {/* 4. Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <Toaster />
    </>
  );
}