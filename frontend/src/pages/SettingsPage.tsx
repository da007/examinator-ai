// Полностью замените содержимое src/pages/SettingsPage.tsx
import { 
  Sun, 
  Moon, 
  Monitor, 
  MessageSquare, 
  Layout, 
  Check,
  Palette,
  Layers
} from 'lucide-react';
import { useAppStore } from '@/store/useAppStore';
import { clsx } from 'clsx';
import { PageHeader } from '@/components/PageHeader';
import type { ReactNode } from 'react';

export function SettingsPage() {
  const { 
    theme, 
    setTheme, 
    examViewMode, 
    setExamViewMode 
  } = useAppStore();

  return (
    <div className="min-h-full bg-app/20 flex flex-col">
      <PageHeader 
        title="Настройки" 
        subtitle="Персонализация интерфейса и выбор режима тестирования"
      />

      <main className="max-w-4xl mx-auto p-8 w-full space-y-12 animate-in fade-in slide-in-from-bottom-4 duration-500">
        
        {/* ── СЕКЦИЯ 1: ЦВЕТОВАЯ СХЕМА ── */}
        <section>
          <h2 className="text-[10px] font-black uppercase tracking-[0.2em] text-muted-app mb-6 flex items-center gap-2 px-2">
            <Palette size={14} /> Внешний вид
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <ThemeCard 
              active={theme === 'light'} 
              onClick={() => setTheme('light')}
              icon={<Sun size={20} />}
              label="Светлая"
            />
            <ThemeCard 
              active={theme === 'dark'} 
              onClick={() => setTheme('dark')}
              icon={<Moon size={20} />}
              label="Темная"
            />
            <ThemeCard 
              active={theme === 'system'} 
              onClick={() => setTheme('system')}
              icon={<Monitor size={20} />}
              label="Системная"
            />
          </div>
        </section>

        {/* ── СЕКЦИЯ 2: РЕЖИМ ЭКЗАМЕНА ── */}
        <section>
          <h2 className="text-[10px] font-black uppercase tracking-[0.2em] text-muted-app mb-6 flex items-center gap-2 px-2">
            <Layers size={14} /> Интерфейс экзамена
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <ModeCard 
              active={examViewMode === 'chat'} 
              onClick={() => setExamViewMode('chat')}
              icon={<MessageSquare size={24} />}
              title="Интерактивный чат"
              description="Последовательная подача вопросов в формате диалога. Идеально для концентрации на одной задаче."
            />
            <ModeCard 
              active={examViewMode === 'standard'} 
              onClick={() => setExamViewMode('standard')}
              icon={<Layout size={24} />}
              title="Классический вид"
              description="Традиционный интерфейс с оглавлением. Удобен для свободного переключения между вопросами."
            />
          </div>
        </section>

        <footer className="pt-10 border-t border-app">
          <div className="bg-primary/5 border border-primary/10 p-4 rounded-2xl flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
            <p className="text-[11px] font-medium text-primary/80 italic">
              Все настройки сохраняются мгновенно в вашем браузере.
            </p>
          </div>
        </footer>
      </main>
    </div>
  );
}

// ── ВСПОМОГАТЕЛЬНЫЕ КОМПОНЕНТЫ ──
interface ThemeCardProps {
  active: boolean;
  onClick: () => void;
  icon: ReactNode;
  label: string;
}

interface ModeCardProps {
  active: boolean;
  onClick: () => void;
  icon: ReactNode;
  title: string;
  description: string;
}

function ThemeCard({ active, onClick, icon, label }: ThemeCardProps) {
  return (
    <button 
      onClick={onClick}
      className={clsx(
        "flex items-center justify-between p-5 rounded-2xl border-2 transition-all active:scale-[0.98]",
        active 
          ? "border-primary bg-primary/5 text-primary shadow-lg shadow-primary/5" 
          : "border-app bg-surface text-muted-app hover:border-primary/30"
      )}
    >
      <div className="flex items-center gap-3">
        <div className={clsx("p-2 rounded-lg", active ? "bg-primary text-white" : "bg-app")}>
          {icon}
        </div>
        <span className="text-sm font-bold">{label}</span>
      </div>
      {active && <Check size={18} strokeWidth={3} />}
    </button>
  );
}

function ModeCard({ active, onClick, icon, title, description }: ModeCardProps) {
  return (
    <button 
      onClick={onClick}
      className={clsx(
        "flex flex-col items-start p-8 rounded-[2rem] border-2 text-left transition-all group active:scale-[0.99]",
        active 
          ? "border-primary bg-surface shadow-xl shadow-primary/5" 
          : "border-app bg-surface/50 hover:border-primary/30"
      )}
    >
      <div className={clsx(
        "p-4 rounded-2xl mb-6 transition-all",
        active ? "bg-primary text-white shadow-lg shadow-primary/20" : "bg-app text-muted-app group-hover:text-primary"
      )}>
        {icon}
      </div>
      <div className="flex items-center gap-3 mb-3">
        <h3 className={clsx("font-black text-lg tracking-tight", active ? "text-app" : "text-muted-app")}>{title}</h3>
        {active && <div className="h-2 w-2 rounded-full bg-primary animate-ping" />}
      </div>
      <p className="text-sm text-muted-app leading-relaxed font-medium">{description}</p>
    </button>
  );
}