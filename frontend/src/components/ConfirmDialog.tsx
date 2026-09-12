import { clsx } from 'clsx';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  confirmVariant?: 'danger' | 'primary';
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = 'Подтвердить',
  cancelLabel = 'Отмена',
  confirmVariant = 'danger',
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[9998] flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onCancel} />
      <div className="relative bg-surface border border-app rounded-2xl shadow-2xl p-6 w-full max-w-sm mx-4 animate-in zoom-in-95 duration-200">
        <h3 className="text-base font-black text-app mb-2">{title}</h3>
        {description && <p className="text-sm text-muted-app mb-6">{description}</p>}
        <div className="flex gap-3 justify-end">
          <button
            onClick={onCancel}
            className="px-5 py-2 rounded-xl text-sm font-bold border border-app text-app hover:bg-surface-alt transition-colors"
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            className={clsx(
              "px-5 py-2 rounded-xl text-sm font-bold text-white transition-colors",
              confirmVariant === 'danger' ? "bg-destructive hover:opacity-90" : "bg-primary hover:bg-primary-hover"
            )}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}