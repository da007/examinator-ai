import { LucideIcon } from 'lucide-react';
import { clsx } from 'clsx';

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({ icon: Icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={clsx(
      "flex flex-col items-center justify-center p-12 text-center animate-in fade-in zoom-in-95 duration-500",
      className
    )}>
      <div className="w-20 h-20 bg-app rounded-[2rem] flex items-center justify-center mb-6 border border-app shadow-inner">
        <Icon size={32} className="text-muted-app opacity-40" />
      </div>
      <h3 className="text-lg font-bold text-app mb-2">{title}</h3>
      <p className="text-sm text-muted-app max-w-xs mx-auto leading-relaxed mb-8">
        {description}
      </p>
      {action && (
        <div className="flex justify-center">
          {action}
        </div>
      )}
    </div>
  );
}