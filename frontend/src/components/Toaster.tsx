import { useNotificationStore } from '@/store/useNotificationStore';
import { AlertCircle, AlertTriangle, CheckCircle2, Info, X } from 'lucide-react';
import { clsx } from 'clsx';

export function Toaster() {
  const { notifications, dismiss } = useNotificationStore();

  return (
    <div className="fixed bottom-6 right-6 z-[9999] flex flex-col gap-3 w-full max-w-[380px]">
      {notifications.map((n) => (
        <div
          key={n.id}
          className={clsx(
            "flex items-start gap-3 p-4 rounded-lg border shadow-lg animate-in slide-in-from-right-5 duration-300",
            n.type === 'success' && "bg-surface border-success/30 text-success",
            n.type === 'error'   && "bg-surface border-destructive/30 text-destructive",
            n.type === 'info'    && "bg-surface border-primary/30 text-primary",
            n.type === 'warning' && "bg-surface border-warning/30 text-warning",
          )}
        >
          <div className="mt-0.5">
            {n.type === 'success' && <CheckCircle2 size={18} />}
            {n.type === 'error'   && <AlertCircle size={18} />}
            {n.type === 'info'    && <Info size={18} />}
            {n.type === 'warning' && <AlertTriangle size={18} />}
          </div>
          <p className="text-sm font-medium flex-1 text-app leading-tight">{n.message}</p>
          <button onClick={() => dismiss(n.id)} className="text-muted-app hover:text-app transition-colors">
            <X size={16} />
          </button>
        </div>
      ))}
    </div>
  );
}