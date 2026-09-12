import { Outlet, Navigate } from 'react-router-dom';
import { Sidebar } from '@/components/Sidebar';
import { useIsAuthenticated } from '@/store/useAppStore';

export function MainLayout() {
  const isAuthenticated = useIsAuthenticated();

  // Если не авторизован — на логин
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="flex h-screen w-full bg-app overflow-hidden">
      {/* Sidebar должен быть здесь */}
      <Sidebar />

      {/* Основной контент */}
      <main className="flex-1 overflow-y-auto bg-app/10 relative">
        <Outlet />
      </main>
    </div>
  );
}