import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { getPendingReviews } from '@/api/review';
import { 
  ClipboardCheck, 
    BookOpen, 
  AlertTriangle, 
  ChevronRight, 
  Clock
} from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { clsx } from 'clsx';

export function TeacherPendingReviewsPage() {
  const navigate = useNavigate();

  const { data: pending, isLoading } = useQuery({
    queryKey: ['pending-reviews'],
    queryFn: getPendingReviews,
    refetchInterval: 30000, // Автообновление раз в 30 сек
  });

  return (
    <div className="min-h-full bg-app/20 flex flex-col">
      <PageHeader 
        title="Очередь проверки" 
        subtitle="Работы студентов с низкой уверенностью ИИ или аномалиями"
      />

      <main className="max-w-5xl mx-auto p-8 w-full">
        {isLoading ? (
          <div className="p-12 text-center animate-pulse text-muted-app uppercase font-bold tracking-widest text-xs">
            Загрузка очереди...
          </div>
        ) : !pending || pending.length === 0 ? (
          <div className="bg-surface border-2 border-dashed border-app rounded-[2.5rem] p-20 text-center">
            <div className="w-20 h-20 rounded-3xl bg-success/10 text-success flex items-center justify-center mx-auto mb-6">
              <ClipboardCheck size={40} />
            </div>
            <h3 className="text-xl font-bold text-app">Все проверено!</h3>
            <p className="text-muted-app text-sm mt-2 max-w-sm mx-auto">
              На данный момент нет работ, требующих вашего вмешательства. ИИ справляется самостоятельно.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between px-4 mb-6">
               <span className="text-[10px] font-black text-muted-app uppercase tracking-[0.2em]">
                 Всего в очереди: {pending.length}
               </span>
            </div>

            {pending.map((item: any) => {
              const confPct = Math.round(item.avgConfidence * 100);
              
              return (
                <div 
                  key={item.sessionId}
                  onClick={() => navigate(`/exam/${item.sessionId}/result`)}
                  className="bg-surface border border-app rounded-2xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-6 hover:shadow-xl hover:border-warning/30 transition-all cursor-pointer group"
                >
                  <div className="flex items-center gap-5 flex-1">
                    <div className={clsx(
                      "w-14 h-14 rounded-2xl shrink-0 flex items-center justify-center border-2",
                      confPct < 40 ? "bg-destructive/5 border-destructive/20 text-destructive" : "bg-warning/5 border-warning/20 text-warning"
                    )}>
                      <AlertTriangle size={28} className={confPct < 40 ? "animate-pulse" : ""} />
                    </div>
                    
                    <div className="min-w-0">
                      <h3 className="font-bold text-lg text-app truncate group-hover:text-primary transition-colors">
                        {item.studentName}
                      </h3>
                      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1">
                        <span className="text-sm text-muted-app font-medium flex items-center gap-1.5">
                          <BookOpen size={14} /> {item.lectureTitle}
                        </span>
                        <span className="text-[10px] font-mono text-muted-app uppercase flex items-center gap-1">
                          <Clock size={12} /> {new Date(item.createdAt).toLocaleString()}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-8 shrink-0 border-t md:border-t-0 md:border-l border-app pt-4 md:pt-0 md:pl-8">
                    <div className="text-right">
                      <p className="text-[9px] uppercase font-black text-muted-app tracking-widest mb-1">AI Confidence</p>
                      <p className={clsx(
                        "text-xl font-black leading-none",
                        confPct < 40 ? "text-destructive" : "text-warning"
                      )}>
                        {confPct}%
                      </p>
                    </div>
                    
                    <button className="p-3 bg-app rounded-xl text-muted-app group-hover:bg-primary group-hover:text-white transition-all shadow-sm">
                      <ChevronRight size={20} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}