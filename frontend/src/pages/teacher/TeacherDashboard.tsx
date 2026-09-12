import { useQuery } from '@tanstack/react-query';
import { useNavigate} from 'react-router-dom';
import { getTeacherDashboard } from '@/api/analytics';
import { getLectures } from '@/api/lecture';
import {
  Users, BookOpen, ClipboardCheck, MessageSquare,
  Plus, BarChart2,
  Play, Sparkles, ChevronRight
} from 'lucide-react';
import { clsx } from 'clsx';
import { PageHeader } from '@/components/PageHeader';
import { StatusStepIndicator } from '@/components/StatusStepIndicator';

export function TeacherDashboard() {
  const navigate = useNavigate();

  // 1. Данные аналитики
  const { data: stats, isLoading: isStatsLoading } = useQuery({
    queryKey: ['teacher-dashboard'],
    queryFn: getTeacherDashboard,
    refetchInterval: 15000,
    staleTime: 0,
  });

  // 2. Данные лекций
  const { data: lectures, isLoading: isLecturesLoading } = useQuery({
    queryKey: ['lectures-management'],
    queryFn: getLectures,
    refetchInterval: 10000,
    staleTime: 0,
  });

  if (isStatsLoading || isLecturesLoading) {
    return (
      <div className="p-12 flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        <p className="text-sm font-medium text-muted-app animate-pulse uppercase tracking-widest">Сбор данных...</p>
      </div>
    );
  }

  const pendingLectures = lectures?.filter((l) =>
    ['draft', 'processing', 'generating', 'review_required'].includes(l.status)
  ) || [];

  

  const cards = [
    { label: 'Студентов',       value: stats?.totalStudents,      icon: Users,         color: 'text-primary',  bg: 'bg-primary/10',  link: null },
    { label: 'Дисциплины',      value: stats?.activeSubjects,     icon: BookOpen,      color: 'text-indigo-500', bg: 'bg-indigo-500/10', link: null },
    { label: 'Активных лекций', value: stats?.activeLectures,     icon: BookOpen,      color: 'text-indigo-500', bg: 'bg-indigo-500/10', link: '/teacher/lectures' },
    { label: 'На проверку',     value: stats?.pendingReviewsCount, icon: ClipboardCheck, color: 'text-amber-500', bg: 'bg-amber-500/10', link: '/teacher/reviews' },
    { label: 'Апелляции',       value: stats?.pendingAppealsCount, icon: MessageSquare, color: 'text-rose-500',  bg: 'bg-rose-500/10',  link: '/teacher/appeals' },
  ];

  return (
    <div className="min-h-full bg-app/20 pb-20">
      <PageHeader
        title="Панель управления"
        subtitle="Обзор активности и мониторинг подготовки материалов"
        actions={
          <button
            onClick={() => navigate('/teacher/upload')}
            className="bg-primary text-white px-5 py-2.5 rounded-xl text-sm font-bold flex items-center gap-2 hover:bg-primary-hover transition-all shadow-lg shadow-primary/20"
          >
            <Plus size={18} /> Новая лекция
          </button>
        }
      />

      <main className="max-w-7xl mx-auto p-8 space-y-10">

        {/* ── БЛОК 1: ЛЕКЦИИ В РАБОТЕ ── */}
        {pendingLectures.length > 0 && (
          <section className="animate-in fade-in slide-in-from-top-4 duration-500">
            <h3 className="text-xs font-black uppercase tracking-[0.2em] text-muted-app mb-6 flex items-center gap-2 px-2">
              <Sparkles size={14} className="text-primary" /> Подготовка контента ИИ
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {pendingLectures.map((lecture) => (
                <div key={lecture.id} className="bg-surface border border-primary/20 rounded-3xl p-6 shadow-sm flex flex-col justify-between group hover:border-primary/40 transition-all">
                  <div className="flex justify-between items-start mb-4">
                    <div className="min-w-0">
                      <h4 className="font-bold text-app truncate text-base">{lecture.title}</h4>
                      <p className="text-[10px] text-muted-app font-medium uppercase mt-1">
                        Добавлено: {new Date(lecture.createdAt).toLocaleDateString()}
                      </p>
                    </div>
                    {lecture.status === 'review_required' && (
                      <button
                        onClick={() => navigate(`/teacher/moderation/${lecture.id}`)}
                        className="bg-primary text-white px-4 py-1.5 rounded-lg text-[10px] font-black uppercase shadow-lg shadow-primary/20 flex items-center gap-2 animate-bounce"
                      >
                        МОДЕРАЦИЯ <Play size={10} />
                      </button>
                    )}
                  </div>
                  <div className="bg-app/30 rounded-2xl p-3 border border-app">
                    <StatusStepIndicator status={lecture.status} />
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* ── БЛОК 2: СТАТИСТИКА ── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-6">
          {cards.map((card) => {
            const inner = (
              <>
                <div className="flex items-center justify-between mb-4">
                  <div className={clsx("p-3 rounded-xl", card.bg, card.color)}>
                    <card.icon size={22} />
                  </div>
                  {card.value != null && card.value > 0 && (
                    <div className="h-1.5 w-1.5 rounded-full bg-primary animate-ping" />
                  )}
                </div>
                <p className="text-3xl font-black text-app tracking-tight">{card.value ?? 0}</p>
                <p className="text-[10px] text-muted-app font-bold mt-1 uppercase tracking-widest">{card.label}</p>
              </>
            );
            return card.link ? (
              <button
                key={card.label}
                onClick={() => navigate(card.link!)}
                className="bg-surface border border-app p-6 rounded-2xl shadow-sm text-left hover:border-primary/50 transition-colors cursor-pointer"
              >
                {inner}
              </button>
            ) : (
              <div key={card.label} className="bg-surface border border-app p-6 rounded-2xl shadow-sm">
                {inner}
              </div>
            );
          })}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">
          {/* ── ТАБЛИЦА ПОСЛЕДНЕЙ АКТИВНОСТИ ── */}
          <section className="lg:col-span-2">
            <h3 className="text-xs font-black uppercase tracking-[0.2em] text-muted-app mb-6 px-2">Последние результаты студентов</h3>
            <div className="bg-surface border border-app rounded-3xl overflow-hidden shadow-sm">
              <table className="w-full text-left">
                <thead>
                  <tr className="bg-app/30 text-[10px] uppercase tracking-widest text-muted-app border-b border-app">
                    <th className="px-6 py-4 font-bold">Дисциплина / Дата</th>
                    <th className="px-6 py-4 font-bold">Студент</th>
                    <th className="px-6 py-4 font-bold text-right">Отчет</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-app">
                  {(stats?.recentActivity ?? []).map((act: any, idx: number) => {
                    const sId = act.sessionId || act.session_id;
                    return (
                      <tr
                        key={sId || idx}
                        className="group hover:bg-app/40 transition-colors cursor-pointer"
                        onClick={() => sId && navigate(`/exam/${sId}/result`)}
                      >
                        <td className="px-6 py-5">
                          <p className="text-sm font-bold text-app group-hover:text-primary transition-colors">
                            {act.lectureTitle || act.lecture_title}
                          </p>
                          <p className="text-[10px] text-muted-app mt-1 font-mono uppercase">
                            {new Date(act.date).toLocaleString()}
                          </p>
                        </td>
                        <td className="px-6 py-5">
                          <span className="text-xs font-mono text-muted-app">
                            {(act.studentId || act.student_id)?.split('-')[0] || 'ID'}...
                          </span>
                        </td>
                        <td className="px-6 py-5 text-right">
                          <ChevronRight size={18} className="text-muted-app group-hover:text-primary transition-all ml-auto" />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>

          {/* ── БОКОВАЯ ПАНЕЛЬ ── */}
          <aside className="space-y-6">
            <h3 className="text-xs font-black uppercase tracking-[0.2em] text-muted-app px-2">Состояние системы</h3>
            <div className="bg-surface border border-app rounded-3xl p-6 shadow-sm space-y-8">
              <div className="space-y-4">
                <div className="flex justify-between items-end">
                  <span className="text-[10px] font-bold uppercase text-muted-app tracking-widest">Аномалии (Антиплагиат)</span>
                  <span className={clsx("text-lg font-black", stats?.totalSuspiciousCount ? "text-rose-500" : "text-success")}>
                    {stats?.totalSuspiciousCount ?? 0}
                  </span>
                </div>
                <div className="h-2 w-full bg-app rounded-full overflow-hidden p-0.5 border border-app">
                  <div
                    className="h-full bg-rose-500 rounded-full transition-all duration-1000"
                    style={{ width: `${Math.min((stats?.totalSuspiciousCount || 0) * 10, 100)}%` }}
                  />
                </div>
              </div>

              {/*
                ИСПРАВЛЕНО: кнопка "Детальная аналитика" теперь ведёт на /teacher/lectures,
                где можно выбрать конкретную лекцию. Прямой переход /teacher/analytics
                без lectureId приводил к пустой странице.
              */}
              <button
                onClick={() => navigate('/teacher/lectures')}
                className="w-full flex items-center justify-center gap-2 py-3 bg-app border border-app rounded-xl text-[11px] font-bold uppercase tracking-widest hover:bg-surface-alt transition-all"
              >
                <BarChart2 size={16} /> Детальная аналитика
              </button>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}