import { Loader2, CheckCircle2, FileSearch, BrainCircuit, ShieldCheck } from 'lucide-react';
import { clsx } from 'clsx';
import { LectureStatus } from '@/types';

interface Props {
  status: LectureStatus;
}

export function StatusStepIndicator({ status }: Props) {
  // Карта этапов для визуализации прогресса
  const steps = [
    { 
      key: 'processing', 
      label: 'Анализ текста', 
      icon: FileSearch, 
      active: status === 'processing' 
    },
    { 
      key: 'generating', 
      label: 'Генерация вопросов', 
      icon: BrainCircuit, 
      active: status === 'generating' 
    },
    { 
      key: 'review_required', 
      label: 'Финальная сборка', 
      icon: ShieldCheck, 
      active: status === 'review_required' 
    },
  ];

  if (status === 'published' || status === 'archived') return null;

  return (
    <div className="flex items-center gap-6 py-2 px-4 bg-primary/5 rounded-2xl border border-primary/10">
      {steps.map((step, idx) => {
        const isPast = steps.findIndex(s => s.active) > idx || status === 'review_required';
        const isCurrent = step.active;

        return (
          <div key={step.key} className="flex items-center gap-2">
            <div className={clsx(
              "flex items-center justify-center w-6 h-6 rounded-lg transition-all",
              isPast ? "bg-success text-white" : 
              isCurrent ? "bg-primary text-white animate-pulse" : "bg-app text-muted-app"
            )}>
              {isPast ? <CheckCircle2 size={14} /> : <step.icon size={14} />}
            </div>
            <span className={clsx(
              "text-[10px] font-black uppercase tracking-tight",
              isCurrent ? "text-primary" : "text-muted-app opacity-60"
            )}>
              {step.label}
            </span>
            {idx < steps.length - 1 && (
              <div className="w-4 h-px bg-app ml-2" />
            )}
          </div>
        );
      })}
      {status !== 'review_required' && (
        <Loader2 size={12} className="animate-spin text-primary ml-auto" />
      )}
    </div>
  );
}