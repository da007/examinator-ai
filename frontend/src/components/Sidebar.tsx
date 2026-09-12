import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, BookOpen, Settings, LogOut,
  Upload, BarChart3, MessageSquare, ChevronLeft, ChevronRight,
  ClipboardCheck
} from 'lucide-react';
import { useCurrentUser, useAppStore } from '@/store/useAppStore';
import { clsx } from 'clsx';

export function Sidebar() {
  const user = useCurrentUser();
  const logout = useAppStore((s) => s.logout);
  const { sidebarCollapsed, setSidebarCollapsed } = useAppStore(); // <--- Подключаем стор

  if (!user) return <aside className="w-64 border-r border-app bg-surface h-full animate-pulse" />;

  const isTeacher = ['teacher', 'admin', 'ta'].includes(user.role);
  const isStudent = ['student', 'admin'].includes(user.role);

  return (
    <aside className={clsx(
      "border-r border-app bg-surface flex flex-col flex-shrink-0 h-full shadow-sm transition-all duration-300 relative",
      sidebarCollapsed ? "w-20" : "w-64"
    )}>
      {/* КНОПКА СВОРАЧИВАНИЯ */}
      <button 
        onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
        className="absolute -right-3 top-10 w-6 h-6 bg-surface border border-app rounded-full flex items-center justify-center text-muted-app hover:text-primary z-50 shadow-sm"
      >
        {sidebarCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
      </button>

      {/* 1. БРЕНДИНГ */}
      <div className={clsx("p-6 mb-2 flex items-center", sidebarCollapsed ? "justify-center" : "gap-3")}>
        <div className="bg-primary text-primary-fg min-w-[36px] h-9 rounded-xl flex items-center justify-center font-bold shadow-lg shadow-primary/20">
          ⬡
        </div>
        {!sidebarCollapsed && (
          <div className="flex flex-col animate-in fade-in duration-500">
            <span className="font-black tracking-tighter text-lg leading-none text-app">EXAMINATOR</span>
            <span className="text-[9px] font-bold text-primary tracking-[0.2em] uppercase mt-1">AI Platform</span>
          </div>
        )}
      </div>

      {/* 2. НАВИГАЦИЯ */}
      <nav className="flex-1 px-4 space-y-8 overflow-y-auto custom-scrollbar">
        {isStudent && (
          <div className="space-y-1">
            {!sidebarCollapsed && <p className="px-4 text-[10px] font-bold text-muted-app uppercase tracking-[0.2em] mb-3">Обучение</p>}
            <NavItem to="/dashboard" icon={LayoutDashboard} label="Экзамены" collapsed={sidebarCollapsed} />
            <NavItem to="/lectures" icon={BookOpen} label="Мои результаты" collapsed={sidebarCollapsed} />
          </div>
        )}

        {isTeacher && (
          <div className="space-y-1">
            {!sidebarCollapsed && <p className="px-4 text-[10px] font-bold text-muted-app uppercase tracking-[0.2em] mb-3">Управление</p>}
            <NavItem to="/teacher/dashboard" icon={BarChart3} label="Аналитика" collapsed={sidebarCollapsed} />
            <NavItem to="/teacher/upload" icon={Upload} label="Загрузка" collapsed={sidebarCollapsed} />
            <NavItem to="/teacher/lectures" icon={BookOpen} label="Лекции" collapsed={sidebarCollapsed} />
            <NavItem to="/teacher/reviews" icon={ClipboardCheck} label="Проверка" collapsed={sidebarCollapsed} />
            <NavItem to="/teacher/appeals" icon={MessageSquare} label="Апелляции" collapsed={sidebarCollapsed} />
          </div>
        )}
      </nav>

      {/* 3. НИЖНЯЯ ПАНЕЛЬ */}
      <div className="p-4 mt-auto border-t border-app bg-app/5">
        <NavItem to="/settings" icon={Settings} label="Настройки" collapsed={sidebarCollapsed} />
        {!sidebarCollapsed && (
           <div className="mt-4 p-3 bg-surface border border-app rounded-2xl animate-in slide-in-from-bottom-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-black truncate max-w-[120px]">{user.fullName || user.email}</span>
                <button onClick={logout} className="p-1.5 text-muted-app hover:text-destructive"><LogOut size={16}/></button>
              </div>
           </div>
        )}
      </div>
    </aside>
  );
}

function NavItem({ to, icon: Icon, label, collapsed }: { to: string; icon: any; label: string; collapsed: boolean }) {
  return (
    <NavLink
      to={to}
      title={collapsed ? label : ""}
      className={({ isActive }) => clsx(
        "flex items-center rounded-xl text-sm font-bold transition-all group",
        collapsed ? "justify-center h-12 w-12 mx-auto" : "gap-3 px-4 py-2.5",
        isActive ? "bg-primary text-primary-fg shadow-md shadow-primary/20" : "text-muted-app hover:bg-app hover:text-app"
      )}
    >
      <Icon size={18} className="shrink-0" />
      {!collapsed && <span className="truncate">{label}</span>}
    </NavLink>
  );
}