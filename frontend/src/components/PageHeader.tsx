// 1. Создаем файл src/components/PageHeader.tsx
import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { clsx } from 'clsx';

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  backTo?: string;
  actions?: React.ReactNode;
  leftAction?: React.ReactNode; // <--- ДОБАВИТЬ ЭТО
  sticky?: boolean;
}

export function PageHeader({ title, subtitle, backTo, actions, leftAction, sticky = true }: PageHeaderProps) {
  const navigate = useNavigate();

  return (
    <header className={clsx(
      "border-b border-app bg-surface px-8 py-5 flex items-center justify-between z-20",
      sticky && "sticky top-0"
    )}>
      <div className="flex items-center gap-4">
        {/* Приоритет: либо кастомное действие (бургер), либо кнопка Назад */}
        {leftAction} 
        
        {backTo && !leftAction && (
          <button
            onClick={() => navigate(backTo)}
            className="p-2 -ml-2 hover:bg-app rounded-full transition-colors text-muted-app hover:text-app"
            title="Назад"
          >
            <ArrowLeft size={20} />
          </button>
        )}
        
        <div>
          <h1 className="text-xl font-bold text-app tracking-tight leading-none">{title}</h1>
          {subtitle && <p className="text-xs text-muted-app mt-1 font-medium">{subtitle}</p>}
        </div>
      </div>

      {actions && <div className="flex items-center gap-3">{actions}</div>}
    </header>
  );
}