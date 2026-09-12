import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getLectureAnalytics, exportSubjectGrades } from '@/api/analytics';
import { getLecture } from '@/api/lecture';
import { EmptyState } from '@/components/EmptyState';
import {
  ArrowLeft, Target, BrainCircuit,
  FileDown, Users, BarChart3,
  Clock, CheckCircle2, AlertCircle, PlayCircle, UserMinus,
  TrendingDown
} from 'lucide-react';
import { clsx } from 'clsx';
import { PageHeader } from '@/components/PageHeader';
import { notify } from '@/store/useNotificationStore';

export function AnalyticsPage() {
  const { lectureId } = useParams<{ lectureId: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'charts' | 'students'>('charts');

  // 1. Загрузка данных
  const { data: lecture } = useQuery({
    queryKey: ['lecture-details', lectureId],
    queryFn: () => getLecture(lectureId!),
    enabled: !!lectureId,
  });

  const { data: stats, isLoading } = useQuery({
    queryKey: ['lecture-analytics', lectureId],
    queryFn: () => getLectureAnalytics(lectureId!),
    enabled: !!lectureId,
    refetchInterval: 30000,
    staleTime: 0,
  });

  const handleExport = async () => {
    if (!lecture) return;
    try {
      notify('info', 'Генерация Excel-ведомости...');
      await exportSubjectGrades(lecture.subjectId, lecture.title);
      notify('success', 'Ведомость успешно загружена');
    } catch {
      notify('error', 'Ошибка при экспорте данных');
    }
  };

  if (isLoading) return (
    <div className="p-20 flex flex-col items-center justify-center min-h-[60vh] gap-4">
      <div className="h-10 w-10 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      <p className="text-xs font-black text-muted-app uppercase tracking-[0.2em] animate-pulse">Агрегация данных...</p>
    </div>
  );

  if (!stats) return (
    <div className="p-20 text-center bg-app/10 m-8 rounded-[2.5rem] border-2 border-dashed border-app">
      <AlertCircle size={48} className="mx-auto text-muted-app opacity-20 mb-4" />
      <h3 className="text-xl font-bold text-app">Аналитика пока недоступна</h3>
      <p className="text-muted-app text-sm mt-2 max-w-xs mx-auto">Данные появятся сразу после того, как первый студент завершит этот экзамен.</p>
      <button onClick={() => navigate('/teacher/lectures')} className="mt-8 text-primary font-bold text-xs uppercase flex items-center gap-2 mx-auto hover:underline">
        <ArrowLeft size={14} /> Вернуться назад
      </button>
    </div>
  );

  const totalStudents = Array.isArray(stats.attendance) ? stats.attendance.length : 0;
  const attendedStudents = Array.isArray(stats.attendance) 
  ? stats.attendance.filter(s => s.status === 'completed').length 
  : 0;
  const attendanceRate = totalStudents > 0 ? Math.round((attendedStudents / totalStudents) * 100) : 0;

  return (
    <div className="min-h-full bg-app/20 flex flex-col pb-20">
      <PageHeader
        title={lecture?.title || 'Аналитика лекции'}
        subtitle="Аналитический отчет и мониторинг успеваемости группы"
        backTo="/teacher/lectures"
        actions={
          <button
            onClick={handleExport}
            className="flex items-center gap-2 px-6 py-2.5 bg-success text-white rounded-xl text-xs font-black hover:opacity-90 transition-all shadow-lg shadow-success/20"
          >
            <FileDown size={16} /> ЭКСПОРТ (XLSX)
          </button>
        }
      />

      <main className="max-w-7xl mx-auto p-8 w-full space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
        
        {/* ── ТАБЫ ── */}
        <div className="flex bg-surface p-1 rounded-2xl border border-app w-fit shadow-sm">
          <button
            onClick={() => setActiveTab('charts')}
            className={clsx(
              "flex items-center gap-2 px-6 py-2.5 rounded-xl text-xs font-black transition-all",
              activeTab === 'charts' ? "bg-primary text-white shadow-lg shadow-primary/20" : "text-muted-app hover:text-app"
            )}
          >
            <BarChart3 size={14} /> ОБЩИЕ МЕТРИКИ
          </button>
          <button
            onClick={() => setActiveTab('students')}
            className={clsx(
              "flex items-center gap-2 px-6 py-2.5 rounded-xl text-xs font-black transition-all",
              activeTab === 'students' ? "bg-primary text-white shadow-lg shadow-primary/20" : "text-muted-app hover:text-app"
            )}
          >
            <Users size={14} /> ЖУРНАЛ ГРУППЫ
          </button>
        </div>

        {activeTab === 'charts' ? (
          stats.totalExams === 0 ? (
            <div className="bg-surface border border-app rounded-[2.5rem] py-20 shadow-sm">
              <EmptyState 
                icon={BarChart3}
                title="Данных недостаточно"
                description="Аналитические графики и карта компетенций будут построены автоматически, когда студенты завершат хотя бы один тест."
              />
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 animate-in fade-in zoom-in-95 duration-500">
              
              {/* 1. ГРАФИК РАСПРЕДЕЛЕНИЯ */}
              <section className="bg-surface border border-app rounded-3xl p-8 shadow-sm lg:col-span-2">
                <h3 className="text-xs font-bold uppercase tracking-widest text-muted-app mb-10 flex items-center gap-2">
                  <Target size={14} className="text-primary" /> Распределение баллов в группе
                </h3>
                <div className="flex items-end justify-between h-56 gap-4 px-4 mt-6">
                  {(() => {
                    const counts = stats.gradeDistribution?.counts ?? [];
                    const maxCount = Math.max(...counts, 1);

                    return counts.map((count: number, i: number) => {
                      const bins = stats.gradeDistribution?.bins ?? [];
                      const height = (count / maxCount) * 100;
                      
                      return (
                        // ВАЖНО: Добавлены классы `justify-end h-full`
                        <div key={i} className="flex-1 flex flex-col items-center justify-end h-full gap-2 group relative">
                          <div className="absolute -top-8 text-[10px] font-black opacity-0 group-hover:opacity-100 transition-all bg-app border border-app text-app px-2 py-1 rounded-lg shadow-sm whitespace-nowrap z-10">
                            {count} чел.
                          </div>
                          <div
                            className={clsx(
                              "w-full rounded-t-xl transition-all duration-1000 ease-out",
                              i === 4 ? "bg-success" : i === 0 ? "bg-destructive" : "bg-primary/40"
                            )}
                            style={{ height: `${Math.max(height, 2)}%` }} 
                          />
                          <span className="text-[9px] text-muted-app font-black uppercase shrink-0 mt-1">
                            {bins[i]}
                          </span>
                        </div>
                      );
                    });
                  })()}
                </div>
              </section>

              {/* 2. МЕТРИКИ ИИ */}
              <div className="space-y-6">
                <section className="bg-surface border border-app rounded-3xl p-8 shadow-sm">
                  <h3 className="text-xs font-bold uppercase tracking-widest text-primary mb-8 flex items-center gap-2">
                    <BrainCircuit size={16} /> Проверка ИИ
                  </h3>
                  <div className="space-y-6">
                    <MetricItem label="Уверенность ИИ" value={`${Math.round((stats.aiMetrics?.avgConfidence || 0) * 100)}%`} />
                    {/* <MetricItem label="Время обработки" value={`${stats.aiMetrics?.avgProcessingTime || 0} сек`} color="text-warning" /> */}
                    <MetricItem label="Явка (посещаемость)" value={`${attendanceRate}%`} />
                  </div>
                </section>
              </div>

              {/* 3. КАРТА ОСВОЕНИЯ (HEATMAP) */}
              <section className="bg-surface border border-app rounded-3xl p-8 shadow-sm lg:col-span-3">
                <h3 className="text-xs font-bold uppercase tracking-widest text-muted-app mb-6">Понимание материала по блокам</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  {stats.topicMastery?.map((topic: any, idx: number) => (
                    <div key={idx} className="p-4 rounded-2xl border border-app bg-app/10 relative overflow-hidden group">
                      <div 
                        className={clsx(
                          "absolute bottom-0 left-0 h-1 transition-all",
                          topic.avgScore > 0.7 ? "bg-success" : topic.avgScore > 0.4 ? "bg-warning" : "bg-destructive"
                        )}
                        style={{ width: `${(topic.avgScore || 0) * 100}%` }}
                      />
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-lg font-black">{Math.round((topic.avgScore || 0) * 100)}%</span>
                      </div>
                      <p className="text-xs text-app font-medium line-clamp-2 opacity-70 group-hover:opacity-100 transition-opacity">
                        {topic.topicName}
                      </p>
                    </div>
                  ))}
                </div>
              </section>

              {/* 4. ВОПРОСЫ-КИЛЛЕРЫ */}
              <section className="bg-surface border border-app rounded-3xl p-8 shadow-sm lg:col-span-3">
                <h3 className="text-xs font-bold uppercase tracking-widest text-destructive mb-6 flex items-center gap-2">
                  <TrendingDown size={14} /> Сложнейшие вопросы (требуют разбора)
                </h3>
                
                {/* Добавлена проверка на пустоту массива */}
                {!stats.killerQuestions || stats.killerQuestions.length === 0 ? (
                  <div className="flex flex-col items-center justify-center p-8 text-center bg-app/5 rounded-2xl border border-app border-dashed">
                    <CheckCircle2 size={32} className="text-muted-app opacity-30 mb-3" />
                    <p className="text-sm font-bold text-app">Пробелов не выявлено</p>
                    <p className="text-xs text-muted-app mt-1">Пока нет вопросов, которые вызывали бы массовые затруднения у группы.</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {stats.killerQuestions.map((q: any) => (
                      <div key={q.questionId} className="flex items-center gap-4 p-4 bg-destructive/5 rounded-2xl border border-destructive/10">
                        <div className="text-xl font-black text-destructive bg-white w-14 h-14 rounded-xl flex items-center justify-center shrink-0 shadow-sm">
                          {isFinite(q.successRate) ? Math.round(q.successRate * 100) : 0}%
                        </div>
                        <p className="text-sm font-bold text-app leading-snug line-clamp-3">{q.questionText}</p>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            </div>
          )
        ) : (
          /* ── ВИД 2: АКАДЕМИЧЕСКИЙ ЖУРНАЛ ── */
          <div className="bg-surface border border-app rounded-[2rem] overflow-hidden shadow-sm animate-in fade-in slide-in-from-right-4 duration-500">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-app/30 text-[10px] uppercase tracking-widest text-muted-app border-b border-app">
                  <th className="px-8 py-5 font-black">Студент</th>
                  <th className="px-6 py-5 font-black">Вердикт</th>
                  <th className="px-6 py-5 font-black text-center">Прогресс</th>
                  <th className="px-6 py-5 font-black text-right">Последняя активность</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-app">
                {Array.isArray(stats.attendance) ? stats.attendance.map((student: any) => (
                  <tr key={student.studentId} className={clsx(
                    "group transition-colors",
                    student.isSuspicious ? "bg-destructive/5 hover:bg-destructive/10" : "hover:bg-app/40"
                  )}>
                    <td className="px-8 py-5">
                      <div className="flex flex-col">
                        <span className="text-sm font-bold text-app group-hover:text-primary transition-colors">{student.studentName}</span>
                        <span className="text-[10px] text-muted-app font-mono">{student.studentEmail}</span>
                      </div>
                    </td>
                    <td className="px-6 py-5">
                      <AttendanceStatus student={student} />
                    </td>
                    <td className="px-6 py-5 text-center">
                      <span className={clsx(
                        "text-lg font-black",
                        student.score === null ? "text-muted-app opacity-20" :
                        student.score >= 0.7 ? "text-success" : 
                        student.score >= 0.4 ? "text-warning" : "text-destructive"
                      )}>
                        {student.score !== null ? `${Math.round(student.score * 100)}%` : '—'}
                      </span>
                    </td>
                    <td className="px-6 py-5 text-right">
                      <div className="flex items-center justify-end gap-4">
                        <span className="text-[10px] font-mono text-muted-app uppercase font-bold">
                          {student.lastActivity ? new Date(student.lastActivity).toLocaleString() : 'Нет данных'}
                        </span>
                        {student.status !== 'not_started' && student.sessionId && (
                          <button 
                            onClick={() => navigate(`/exam/${student.sessionId}/result`)}
                            className="p-2 bg-app rounded-lg text-muted-app hover:text-primary hover:bg-primary/10 transition-all group/btn"
                            title="Просмотреть детальные ответы"
                          >
                            <PlayCircle size={16} className="group-hover/btn:scale-110 transition-transform" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={4} className="px-8 py-10 text-center text-sm text-muted-app">
                      Журнал недоступен в данном формате данных.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}

// ── ВСПОМОГАТЕЛЬНЫЕ КОМПОНЕНТЫ ──

function AttendanceStatus({ student }: { student: any }) {
  const { status, score, isSuspicious } = student;
  
  if (isSuspicious) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-full w-fit text-[10px] font-black uppercase tracking-tight bg-destructive text-white animate-pulse">
        <AlertCircle size={14} /> Спорно / Аномалия
      </div>
    );
  }

  if (status === 'active') {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-full w-fit text-[10px] font-black uppercase tracking-tight text-primary bg-primary/10">
        <PlayCircle size={14} /> В процессе
      </div>
    );
  }
  if (status === 'processing') {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-full w-fit text-[10px] font-black uppercase tracking-tight text-warning bg-warning/10">
        <Clock size={14} /> Проверка ИИ
      </div>
    );
  }

  if (status === 'completed' && score !== null) {
    const isPassed = score >= 0.4;
    return (
      <div className={clsx(
        "flex items-center gap-2 px-3 py-1.5 rounded-full w-fit text-[10px] font-black uppercase tracking-tight",
        isPassed ? "bg-success/10 text-success" : "bg-destructive/10 text-destructive"
      )}>
        {isPassed ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
        {isPassed ? `Сдано (${Math.round(score * 100)}%)` : `Не сдано (${Math.round(score * 100)}%)`}
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded-full w-fit text-[10px] font-black uppercase tracking-tight text-muted-app bg-app">
      <UserMinus size={14} /> Не заходил
    </div>
  );
}

function MetricItem({ label, value, color = "text-app" }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex justify-between items-end border-b border-app pb-3">
      <span className="text-[11px] text-muted-app font-bold uppercase tracking-widest">{label}</span>
      <span className={clsx("text-2xl font-black leading-none", color)}>{value}</span>
    </div>
  );
}