import { useState, useMemo } from 'react';
import { useQueryClient, useMutation, useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { getLectures } from '@/api/lecture';
import { getSubjects } from '@/api/subject';
import { createSession, getMySessions } from '@/api/exam';
import { 
  BookOpen, Clock, PlayCircle, Loader2, 
  Search, SortAsc, X
} from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { useCurrentUser } from '@/store/useAppStore';
import { clsx } from 'clsx';
import { notify } from '@/store/useNotificationStore';

type StatusFilter = 'all' | 'available' | 'completed' | 'upcoming' | 'missed';
type SortOption = 'newest' | 'oldest' | 'title';

export function DashboardPage() {
  const navigate = useNavigate();
  const user = useCurrentUser();
  
  // Состояния фильтрации
  const [search, setSearch] = useState('');
  const [selectedSubjectId, setSelectedSubjectId] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [sortBy, setSortBy] = useState<SortOption>('newest');
  const queryClient = useQueryClient();

  // 1. Загрузка данных
  const { data: lectures, isLoading: ldLoading } = useQuery({ queryKey: ['lectures'], queryFn: getLectures });
  const { data: subjects, isLoading: sbLoading } = useQuery({ queryKey: ['subjects'], queryFn: getSubjects });
  const { data: sessions } = useQuery({ queryKey: ['my-sessions'], queryFn: getMySessions });

  const [startingId, setStartingId] = useState<string | null>(null);

  const startExam = useMutation({
    mutationFn: (lectureId: string) => createSession(lectureId),
    onSuccess: (session, lectureId) => {
      queryClient.invalidateQueries({ queryKey: ['my-sessions'] }); // A-3
      setStartingId(null);
      navigate(`/exam/${session.id}`);
    },
    onError: () => {
      setStartingId(null);
      notify('error', 'Не удалось начать экзамен');
    },
  });

  // 2. ГЛАВНАЯ ЛОГИКА ФИЛЬТРАЦИИ И СОРТИРОВКИ
  const filteredLectures = useMemo(() => {
    if (!lectures) return [];
    const now = new Date();

    let result = [...lectures];

    // Фильтр по предмету
    if (selectedSubjectId !== 'all') {
      result = result.filter(l => l.subjectId === selectedSubjectId);
    }

    // Фильтр по поиску
    if (search.trim()) {
      const s = search.toLowerCase();
      result = result.filter(l => l.title.toLowerCase().includes(s));
    }

    // Фильтр по статусу
    if (statusFilter !== 'all') {
      result = result.filter(l => {
        const session = sessions?.find(s => s.lectureId === l.id);
        const openDate = l.openFrom ? new Date(l.openFrom) : null;
        const dueDate = l.deadlineAt ? new Date(l.deadlineAt) : null;
        
        switch (statusFilter) {
          case 'completed': return session?.status === 'completed';
          case 'available': return (!session || session.status === 'active') && (!openDate || now >= openDate) && (!dueDate || now <= dueDate);
          case 'upcoming':  return !session && openDate && now < openDate;
          case 'missed':    return !session && dueDate && now > dueDate;
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
  }, [lectures, subjects, sessions, search, selectedSubjectId, statusFilter, sortBy]);

  const isLoading = ldLoading || sbLoading;

  return (
    <div className="min-h-full bg-app/20 flex flex-col pb-20">
      <PageHeader 
        title="Витрина экзаменов" 
        subtitle="Интеллектуальная система тестирования"
        actions={
          user?.role === 'admin' && <div className="px-3 py-1 bg-primary/10 border border-primary/20 rounded-xl text-[10px] font-black text-primary uppercase tracking-widest">Admin Mode</div>
        }
      />

      <main className="max-w-7xl mx-auto p-8 w-full space-y-6">
        
        {/* ── ПАНЕЛЬ УПРАВЛЕНИЯ (CONTROL BAR) ── */}
        <div className="bg-surface border border-app p-4 rounded-[2rem] shadow-sm space-y-4">
          <div className="flex flex-col lg:flex-row gap-4">
            {/* Поиск */}
            <div className="relative flex-1">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-app" size={18} />
              <input 
                className="w-full bg-app/50 border border-app rounded-2xl pl-12 pr-4 py-3 text-sm outline-none focus:border-primary focus:bg-surface transition-all"
                placeholder="Поиск по названию лекции..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              {search && (
                <button onClick={() => setSearch('')} className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-app hover:text-app">
                  <X size={16} />
                </button>
              )}
            </div>

            {/* Сортировка */}
            <div className="flex items-center gap-2 bg-app/50 border border-app rounded-2xl px-4 py-2">
              <SortAsc size={16} className="text-muted-app" />
              <select 
                className="bg-transparent text-xs font-bold outline-none cursor-pointer"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortOption)}
              >
                <option value="newest">Сначала новые</option>
                <option value="oldest">Сначала старые</option>
                <option value="title">По названию (А-Я)</option>
              </select>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-app/50">
            {/* Статус-фильтры */}
            <div className="flex bg-app/50 p-1 rounded-xl border border-app">
              {(['all', 'available', 'completed', 'upcoming', 'missed'] as StatusFilter[]).map((f) => (
                <button
                  key={f}
                  onClick={() => setStatusFilter(f)}
                  className={clsx(
                    "px-4 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-wider transition-all",
                    statusFilter === f ? "bg-primary text-white shadow-md" : "text-muted-app hover:text-app"
                  )}
                >
                  {f === 'all' ? 'Все' : f === 'available' ? 'Доступные' : f === 'completed' ? 'Сдано' : f === 'upcoming' ? 'Будущие' : 'Пропущено'}
                </button>
              ))}
            </div>

            {/* Предметы-фильтры */}
            <div className="h-6 w-px bg-app mx-2 hidden sm:block" />
            <div className="flex items-center gap-2 overflow-x-auto no-scrollbar max-w-full">
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

        {/* ── СЕТКА ЛЕКЦИЙ ── */}
        {isLoading ? (
          <div className="py-20 text-center"><Loader2 className="animate-spin mx-auto text-primary" size={32} /></div>
        ) : filteredLectures.length === 0 ? (
          <div className="bg-surface border-2 border-dashed border-app rounded-[2rem] p-20 text-center">
            <BookOpen className="text-muted-app opacity-20 mx-auto mb-4" size={48} />
            <h3 className="text-xl font-bold text-app">Ничего не найдено</h3>
            <p className="text-muted-app text-sm mt-1">Попробуйте изменить параметры фильтрации или поиска.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {filteredLectures.map((lecture) => {
              const session = sessions?.find(s => s.lectureId === lecture.id);
              const now = new Date();
              const openDate = lecture.openFrom ? new Date(lecture.openFrom) : null;
              const dueDate = lecture.deadlineAt ? new Date(lecture.deadlineAt) : null;
              const isTooEarly = openDate && now < openDate;
              const isTooLate = dueDate && now > dueDate;

              return (
                <div key={lecture.id} className="bg-surface border border-app rounded-[2.5rem] p-8 flex flex-col hover:border-primary/40 hover:shadow-2xl transition-all group">
                  <div className="flex-1">
                    <div className="flex justify-between items-center mb-6">
                      <div className={clsx(
                        "px-3 py-1 rounded-lg text-[10px] font-black uppercase border",
                        session?.status === 'completed' ? "bg-success/10 text-success border-success/20" :
                        isTooLate && !session ? "bg-destructive/10 text-destructive border-destructive/20" :
                        isTooEarly ? "bg-warning/10 text-warning border-warning/20" : "bg-primary/10 text-primary border-primary/20"
                      )}>
                        {session?.status === 'completed' ? 'Завершено' : isTooLate && !session ? 'Пропущено' : isTooEarly ? 'Ожидание' : 'Активно'}
                      </div>
                      <span className="text-[10px] font-mono text-muted-app uppercase flex items-center gap-1.5"><Clock size={12}/>{new Date(lecture.createdAt).toLocaleDateString()}</span>
                    </div>
                    <h3 className="text-xl font-bold text-app mb-4 leading-tight group-hover:text-primary transition-colors line-clamp-2">{lecture.title}</h3>
                   {(() => {
                    const subject = subjects?.find(s => s.id === lecture.subjectId);
                    return (
                      <div className="mb-8">
                        <div className="text-[9px] font-black text-primary/60 uppercase tracking-widest bg-primary/5 px-2 py-1 rounded border border-primary/10 w-fit mb-2">
                          {subject?.name || 'Общая'}
                        </div>
                        {subject?.description && (
                          <p className="text-[11px] text-muted-app line-clamp-2 leading-relaxed italic">
                            {subject.description}
                          </p>
                        )}
                        {subject?.teacherInfo && (
                          <p className="text-[10px] text-muted-app mt-2 font-medium">
                            Лектор: <span className="text-app">{subject.teacherInfo.fullName}</span>
                          </p>
                        )}
                      </div>
                    );
                  })()}
                  </div>

                  {(() => {
                    if (session) {
                      return <button onClick={() => navigate(session.status === 'active' ? `/exam/${session.id}` : `/exam/${session.id}/result`)} className="w-full flex items-center justify-center gap-3 bg-primary/10 text-primary border border-primary/20 py-4 rounded-2xl text-sm font-black transition-all hover:bg-primary hover:text-white">
                        {session.status === 'active' ? 'ПРОДОЛЖИТЬ' : 'СМОТРЕТЬ РЕЗУЛЬТАТ'}
                      </button>;
                    }
                    if (isTooEarly) {
                      return <div className="w-full p-4 bg-surface-alt border border-app rounded-2xl text-center"><p className="text-[9px] font-black text-muted-app uppercase">Старт в:</p><p className="text-xs font-bold text-app">{openDate?.toLocaleString()}</p></div>;
                    }
                    if (isTooLate) {
                      return <div className="w-full p-4 bg-destructive/5 border border-destructive/20 rounded-2xl text-center"><p className="text-[10px] font-black text-destructive uppercase tracking-widest">ВРЕМЯ ВЫШЛО</p></div>;
                    }
                    return <button
                      onClick={() => { setStartingId(lecture.id); startExam.mutate(lecture.id); }}
                      disabled={startingId === lecture.id}
                      className="w-full flex items-center justify-center gap-3 bg-app border border-app group-hover:bg-primary group-hover:border-primary group-hover:text-primary-fg py-4 rounded-2xl text-sm font-black transition-all shadow-sm"
                    >
                      {startingId === lecture.id ? <Loader2 size={18} className="animate-spin" /> : <PlayCircle size={20} />}
                      {startingId === lecture.id ? 'ПОДГОТОВКА...' : 'НАЧАТЬ ЭКЗАМЕН'}
                    </button>;
                  })()}
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}