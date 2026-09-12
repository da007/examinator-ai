import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getAllAppeals, resolveAppeal } from '@/api/review';
import { notify } from '@/store/useNotificationStore';
import { 
  MessageSquare, 
  CheckCircle, 
  XCircle, 
  Clock, 
  ExternalLink,
  ChevronRight
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { clsx } from 'clsx';

export function AppealsPage() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [comment, setComment] = useState('');

  const { data: appeals, isLoading } = useQuery({
    queryKey: ['teacher-appeals'],
    queryFn: getAllAppeals,
    refetchInterval: 30000,
    staleTime: 0,
  });

  const resolveMutation = useMutation({
    mutationFn: (vars: { id: string, status: 'accepted' | 'rejected' }) => 
      resolveAppeal(vars.id, { status: vars.status, teacherComment: comment }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teacher-appeals'] });
      notify('success', 'Решение по апелляции сохранено');
      setSelectedId(null);
      setComment('');
    }
  });

  const selectedAppeal = appeals?.find(a => a.id === selectedId);

  if (isLoading) return <div className="p-10 animate-pulse">Загрузка заявок...</div>;

  return (
    <div className="flex flex-1 h-full overflow-hidden bg-app">
      {/* ── ЛЕВАЯ ПАНЕЛЬ: СПИСОК ── */}
      <div className="w-1/3 border-r border-app flex flex-col bg-surface">
        <div className="p-6 border-b border-app">
          <h1 className="text-xl font-bold flex items-center gap-2">
            <MessageSquare size={20} className="text-primary" />
            Апелляции
          </h1>
          <p className="text-xs text-muted-app mt-1">Запросы студентов на пересмотр оценок</p>
        </div>

        <div className="flex-1 overflow-y-auto">
          {appeals?.length === 0 ? (
            <div className="p-10 text-center text-muted-app text-sm italic">Нет активных апелляций</div>
          ) : (
            appeals?.map((appeal) => (
              <button
                key={appeal.id}
                onClick={() => { setSelectedId(appeal.id); setComment(''); }}
                className={clsx(
                  "w-full p-5 text-left border-b border-app transition-colors flex items-center justify-between group",
                  selectedId === appeal.id ? "bg-primary/5" : "hover:bg-app/50"
                )}
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={clsx(
                      "w-2 h-2 rounded-full",
                      appeal.status === 'pending' ? "bg-warning" : 
                      appeal.status === 'accepted' ? "bg-success" : "bg-destructive"
                    )} />
                    <span className="text-[10px] font-bold uppercase tracking-wider text-muted-app">
                      {appeal.status}
                    </span>
                  </div>
                  {/* Теперь показываем имя студента жирным шрифтом */}
                  <p className="text-sm font-bold truncate text-app">
                    {appeal.studentName || appeal.studentEmail || 'Анонимный студент'}
                  </p>
                  <p className="text-[10px] text-muted-app font-mono truncate opacity-60">
                    Сессия: {appeal.sessionId.split('-')[0]}...
                  </p>
                  <p className="text-xs text-muted-app mt-1 line-clamp-1 italic">«{appeal.reason}»</p>
                </div>
                <ChevronRight size={16} className="text-muted-app group-hover:translate-x-1 transition-transform" />
              </button>
            ))
          )}
        </div>
      </div>

      {/* ── ПРАВАЯ ПАНЕЛЬ: ДЕТАЛИ ── */}
      <div className="flex-1 overflow-y-auto bg-app/30">
        {selectedAppeal ? (
          <div className="p-10 max-w-2xl mx-auto animate-in fade-in slide-in-from-right-4 duration-300">
            <div className="bg-surface border border-app rounded-2xl p-8 shadow-sm">
              <div className="flex justify-between items-start mb-8">
                <div>
                  <h2 className="text-2xl font-bold">{selectedAppeal.studentName || 'Детали апелляции'}</h2>
                  <p className="text-sm text-primary font-medium">{selectedAppeal.studentEmail}</p>
                  <p className="text-xs text-muted-app flex items-center gap-1.5 mt-1">
                    <Clock size={12} /> Подана: {new Date(selectedAppeal.createdAt).toLocaleString()}
                  </p>
                </div>
                <Link 
                  to={`/exam/${selectedAppeal.sessionId}/result`}
                  className="flex items-center gap-1.5 text-xs font-bold text-primary hover:underline"
                >
                  СМОТРЕТЬ РАБОТУ <ExternalLink size={14} />
                </Link>
              </div>

              <div className="space-y-6">
                <section>
                  <label className="text-[10px] font-bold uppercase tracking-widest text-muted-app block mb-2">Причина студента</label>
                  <div className="p-4 bg-app/50 border border-app rounded-xl text-sm italic text-app leading-relaxed">
                    «{selectedAppeal.reason}»
                  </div>
                </section>

                {selectedAppeal.status === 'pending' ? (
                  <section className="pt-6 border-t border-app space-y-4">
                    <label className="text-[10px] font-bold uppercase tracking-widest text-primary block">Ваш вердикт</label>
                    <textarea 
                      className="w-full bg-surface border border-app rounded-xl p-4 text-sm outline-none focus:border-primary transition-all min-h-[120px]"
                      placeholder="Опишите причину принятия или отклонения..."
                      value={comment}
                      onChange={(e) => setComment(e.target.value)}
                    />
                    <div className="grid grid-cols-2 gap-4">
                      <button 
                        disabled={resolveMutation.isPending}
                        onClick={() => resolveMutation.mutate({ id: selectedAppeal.id, status: 'rejected' })}
                        className="flex items-center justify-center gap-2 p-3 rounded-xl border-2 border-destructive/20 text-destructive font-bold text-xs hover:bg-destructive/5 transition-all"
                      >
                        <XCircle size={16} /> ОТКЛОНИТЬ
                      </button>
                      <button 
                        disabled={resolveMutation.isPending}
                        onClick={() => resolveMutation.mutate({ id: selectedAppeal.id, status: 'accepted' })}
                        className="flex items-center justify-center gap-2 p-3 rounded-xl bg-success text-white font-bold text-xs hover:opacity-90 transition-all shadow-lg shadow-success/20"
                      >
                        <CheckCircle size={16} /> ПРИНЯТЬ
                      </button>
                    </div>
                  </section>
                ) : (
                  <section className="pt-6 border-t border-app">
                    <div className={clsx(
                      "p-4 rounded-xl border flex items-start gap-3",
                      selectedAppeal.status === 'accepted' ? "bg-success/5 border-success/20" : "bg-destructive/5 border-destructive/20"
                    )}>
                      {selectedAppeal.status === 'accepted' ? <CheckCircle size={18} className="text-success" /> : <XCircle size={18} className="text-destructive" />}
                      <div>
                        <p className="text-xs font-bold uppercase tracking-tight">Решение вынесено</p>
                        <p className="text-sm mt-1">{selectedAppeal.teacherComment || 'Без комментария'}</p>
                      </div>
                    </div>
                  </section>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-muted-app opacity-30">
            <MessageSquare size={64} strokeWidth={1} />
            <p className="mt-4 font-medium">Выберите апелляцию для рассмотрения</p>
          </div>
        )}
      </div>
    </div>
  );
}