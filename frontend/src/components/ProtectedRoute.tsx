import { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useIsAuthenticated, useCurrentUser } from '@/store/useAppStore';
import type { UserRole } from '@/types';

interface ProtectedRouteProps {
  children: ReactNode;
  /** Если указаны роли, только пользователи с этими ролями получат доступ */
  allowedRoles?: UserRole[];
}

/**
 * Компонент для защиты маршрутов.
 * Проверяет авторизацию и опционально роль пользователя.
 */
export function ProtectedRoute({ children, allowedRoles }: ProtectedRouteProps) {
  const isAuthenticated = useIsAuthenticated();
  const user = useCurrentUser();
  const location = useLocation();

  // Если токен есть, а юзера еще нет — значит, идет загрузка
  if (isAuthenticated && !user) {
    return <div className="h-screen w-full bg-app flex items-center justify-center">Загрузка профиля...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // 2. Если роль не подходит (если роли были указаны)
  if (allowedRoles && user && !allowedRoles.includes(user.role)) {
    // В случае отсутствия прав отправляем на домашнюю страницу роли (dashboard)
    return <Navigate to={user?.role === 'student' ? '/dashboard' : '/teacher/dashboard'} replace />;
  }

  return <>{children}</>;
}