import { AlertTriangle, Info, XCircle, RefreshCcw } from 'lucide-react';
import type { EventInteraction } from '../domain/interactions';
import { clsx } from 'clsx';

interface Props {
  interaction: EventInteraction;
}

export function EventRenderer({ interaction }: Props) {
  const { label, severity } = interaction;

  return (
    <div className="flex justify-center my-4 animate-in fade-in zoom-in-95 duration-300">
      <div className={clsx(
        "flex items-center gap-2 px-4 py-1.5 rounded-full border text-[11px] font-bold uppercase tracking-wider shadow-sm",
        severity === 'error' && "bg-destructive/5 border-destructive/20 text-destructive",
        severity === 'warning' && "bg-warning/5 border-warning/20 text-warning",
        severity === 'info' && "bg-surface border-app text-muted-app"
      )}>
        {severity === 'error' && <XCircle size={14} />}
        {severity === 'warning' && <AlertTriangle size={14} />}
        {severity === 'info' && <Info size={14} />}
        
        <span>{label}</span>

        {severity === 'error' && (
          <button 
            onClick={() => window.location.reload()} 
            className="ml-2 hover:rotate-180 transition-transform duration-500"
            title="Перезагрузить страницу"
          >
            <RefreshCcw size={12} />
          </button>
        )}
      </div>
    </div>
  );
}