import { useState, useMemo } from 'react';
import { useQueryClient, useQuery, useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { getLectures } from '@/api/lecture';
import { getSubjects } from '@/api/subject';
import { getMySessions, createSession } from '@/api/exam';
import { 
  BookOpen, FileText, CheckCircle2, Clock, 
  PlayCircle, BarChart2, AlertCircle, Search, 
  X, SortAsc, UserMinus
} from 'lucide-react';
import { clsx } from 'clsx';
import { notify } from '@/store/useNotificationStore';
import { PageHeader } from '@/components/PageHeader';

type StatusFilter = 'all' | 'completed' | 'active' | 'missed';
type SortOption = 'newest' | 'oldest' | 'title';

export function LecturesPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Состояния фильтрации
  const [search, setSearch] = useState('');
  const [selectedSubjectId, setSelectedSubjectId] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [sortBy, setSortBy] = useState<SortOption>('newest');

  // 1. Загрузка данных
  const { data: lectures, isLoading: ldLoading } = useQuery({ queryKey: ['lectures'], queryFn: getLectures });
  const { data: subjects, isLoading: sbLoading } = useQuery({ queryKey: ['subjects'], queryFn: getSubjects });
  const { data: sessions, isLoading: ssLoading } = useQuery({ queryKey: ['my-sessions'], queryFn: getMySessions });

  const [startingId, setStartingId] = useState<string | null>(null);

  const startMutation = useMutation({
    mutationFn: (lectureId: string) => createSession(lectureId),
    onSuccess: (session, _lectureId) => {
      queryClient.invalidateQueries({ queryKey: ['my-sessions'] });
      setStartingId(null);
      navigate(`/exam/${session.id}`);
    },
    onError: () => {
      setStartingId(null);
      notify('error', 'Не удалось начать экзамен.');
    },
  });

  // 2. Логика фильтрации и сортировки
  const filteredData = useMemo(() => {
    if (!lectures) return [];
    const now = new Date();
    let result = [...lectures];

    // Поиск
    if (search.trim()) {
      const s = search.toLowerCase();
      result = result.filter(l => l.title.toLowerCase().includes(s));
    }

    // Предмет
    if (selectedSubjectId !== 'all') {
      result = result.filter(l => l.subjectId === selectedSubjectId);
    }

    // Статус (на основе сессий)
    if (statusFilter !== 'all') {
      result = result.filter(l => {
        const session = sessions?.find(s => s.lectureId === l.id);
        const isMissed = !session && l.deadlineAt && now > new Date(l.deadlineAt);

        switch (statusFilter) {
          case 'completed': return session?.status === 'completed';
          case 'active':    return session?.status === 'active' || session?.status === 'processing';
          case 'missed':    return isMissed;
          default: return true;
        }
      });
    }

    // Сортировка
    result.sort((a, b) => {
      if (sortBy === 'title') return a.title.localeCompare(b.title);
      const dateA = new Date(a.createdAt).getTime();
      const dateB = new Date(b.createdAt).getTime();
      return sortBy === 'newest' ? dateB - dateA : dateA - dateB;
    });

    return result;
  }, [lectures, sessions, search, selectedSubjectId, statusFilter, sortBy]);

  const isLoading = ldLoading || sbLoading || ssLoading;

  return (
    <div className="min-h-full bg-app/20 flex flex-col pb-20">
      <PageHeader 
        title="Мои результаты" 
        subtitle="История прохождений, аналитика и статус успеваемости"
      />

      <main className="max-w-5xl mx-auto p-8 w-full space-y-6">
        
        {/* ── ПАНЕЛЬ УПРАВЛЕНИЯ (CONTROL BAR) ── */}
        <div className="bg-surface border border-app p-4 rounded-[2rem] shadow-sm space-y-4">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-app" size={18} />
              <input 
                className="w-full bg-app/50 border border-app rounded-2xl pl-12 pr-4 py-3 text-sm text-app outline-none focus:border-primary transition-all"
                placeholder="Поиск в истории..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              {search && <X size={16} className="absolute right-4 top-1/2 -translate-y-1/2 cursor-pointer text-muted-app" onClick={() => setSearch('')} />}
            </div>

            <div className="flex items-center gap-2 bg-app/50 border border-app rounded-2xl px-4 py-2">
              <SortAsc size={16} className="text-muted-app" />
              <select 
                className="bg-transparent text-xs font-bold outline-none cursor-pointer text-app"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortOption)}
              >
                <option value="newest">Сначала новые</option>
                <option value="oldest">Сначала старые</option>
                <option value="title">По названию</option>
              </select>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-app/50">
            <div className="flex bg-app/50 p-1 rounded-xl border border-app">
              {(['all', 'completed', 'active', 'missed'] as StatusFilter[]).map((f) => (
                <button
                  key={f}
                  onClick={() => setStatusFilter(f)}
                  className={clsx(
                    "px-4 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-wider transition-all",
                    statusFilter === f ? "bg-primary text-white shadow-md" : "text-muted-app hover:text-app"
                  )}
                >
                  {f === 'all' ? 'Все' : f === 'completed' ? 'Сдано' : f === 'active' ? 'В работе' : 'Пропущено'}
                </button>
              ))}
            </div>

            <div className="h-6 w-px bg-app mx-2" />

            <div className="flex items-center gap-2 overflow-x-auto no-scrollbar">
              <button
                onClick={() => setSelectedSubjectId('all')}
                className={clsx(
                  "px-4 py-1.5 rounded-xl text-[10px] font-bold border transition-all whitespace-nowrap",
                  selectedSubjectId === 'all' ? "border-primary text-primary bg-primary/5" : "border-app text-muted-app"
                )}
              >
                Все предметы
              </button>
              {subjects?.map(sub => (
                <button
                  key={sub.id}
                  onClick={() => setSelectedSubjectId(sub.id)}
                  className={clsx(
                    "px-4 py-1.5 rounded-xl text-[10px] font-bold border transition-all whitespace-nowrap",
                    selectedSubjectId === sub.id ? "border-primary text-primary bg-primary/5" : "border-app text-muted-app"
                  )}
                >
                  {sub.name}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* ── СПИСОК РЕЗУЛЬТАТОВ ── */}
        <div className="space-y-4">
          {isLoading ? (
            <div className="p-12 text-center animate-pulse text-muted-app font-bold uppercase tracking-widest text-xs">Загрузка...</div>
          ) : filteredData.length === 0 ? (
            <div className="p-20 text-center border-2 border-dashed border-app rounded-[2rem] bg-surface/50">
              <BookOpen size={48} className="mx-auto text-muted-app opacity-20 mb-4" />
              <p className="text-app font-bold">Ничего не найдено</p>
              <p className="text-xs text-muted-app mt-1">Измените фильтры или поисковый запрос.</p>
            </div>
          ) : (
            filteredData.map((lecture) => {
              const session = sessions?.find(s => s.lectureId === lecture.id);
              const now = new Date();
              const isTooLate = lecture.deadlineAt && now > new Date(lecture.deadlineAt);
              const isCompleted = session?.status === 'completed';

              return (
                <div key={lecture.id} className="bg-surface border border-app rounded-2xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-6 hover:shadow-lg transition-all group">
                  <div className="flex items-center gap-5 flex-1">
                    <div className={clsx(
                      "w-14 h-14 rounded-2xl shrink-0 flex items-center justify-center transition-colors border-2",
                      isCompleted ? "bg-success/10 text-success border-success/20" : 
                      isTooLate && !session ? "bg-destructive/10 text-destructive border-destructive/20" : "bg-primary/10 text-primary border-primary/20"
                    )}>
                      {isCompleted ? <CheckCircle2 size={28} /> : isTooLate && !session ? <UserMinus size={28} /> : <FileText size={28} />}
                    </div>
                    
                    <div className="min-w-0">
                      <h3 className="font-bold text-base text-app truncate group-hover:text-primary transition-colors">{lecture.title}</h3>
                      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1">
                        <span className="text-[10px] font-bold text-muted-app uppercase tracking-wider flex items-center gap-1">
                          <Clock size={12} /> {new Date(lecture.createdAt).toLocaleDateString()}
                        </span>
                        <span className="text-[9px] font-black text-primary/40 uppercase tracking-widest px-2 py-0.5 bg-app rounded border border-app">
                          {subjects?.find(s => s.id === lecture.subjectId)?.name || 'Общая'}
                        </span>
                        {session?.status === 'processing' && <span className="text-[10px] font-black text-warning uppercase animate-pulse flex items-center gap-1"><AlertCircle size={12}/>Проверка ИИ...</span>}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-6 shrink-0 border-t md:border-t-0 md:border-l border-app pt-4 md:pt-0 md:pl-6">
                    {isCompleted && (
                      <div className="text-right hidden sm:block">
                        <p className="text-[9px] uppercase font-black text-muted-app tracking-widest">Результат</p>
                        <p className="text-lg font-black text-success leading-none">СДАНO</p>
                      </div>
                    )}

                    <div className="flex gap-2 min-w-[140px] justify-end">
                      {(() => {
                        if (session && session.status !== 'active') {
                          return <button onClick={() => navigate(`/exam/${session.id}/result`)} className="px-5 py-2.5 bg-app border border-app text-app rounded-xl font-bold text-xs hover:bg-surface-alt transition-all">ОТЧЕТ <BarChart2 size={16} className="inline ml-1"/></button>;
                        }
                        if (session && session.status === 'active') {
                          return <button onClick={() => navigate(`/exam/${session.id}`)} className="px-5 py-2.5 bg-primary text-white rounded-xl font-bold text-xs shadow-md shadow-primary/20 hover:bg-primary-hover transition-all">ПРОДОЛЖИТЬ <PlayCircle size={16} className="inline ml-1"/></button>;
                        }
                        if (isTooLate) {
                          return <div className="px-4 py-2 bg-destructive/5 text-destructive rounded-lg text-[10px] font-black uppercase border border-destructive/10">НЕ ЯВИЛСЯ</div>;
                        }
                        return <button onClick={() => { setStartingId(lecture.id); startMutation.mutate(lecture.id); }} disabled={startingId === lecture.id} className="px-5 py-2.5 bg-primary text-white rounded-xl font-bold text-xs shadow-md shadow-primary/20 hover:bg-primary-hover transition-all">НАЧАТЬ <PlayCircle size={16} className="inline ml-1"/></button>;
                      })()}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </main>
    </div>
  );
}