import { useState } from 'react';
import { useParams} from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getResult, getSession } from '@/api/exam';
import { submitAppeal, getMyAppeals, getAllAppeals, resolveAppeal, correctAnswer } from '@/api/review';
import {
  BrainCircuit,
  MessageSquare, Edit3, ShieldAlert
} from 'lucide-react';
import { clsx } from 'clsx';
import { PageHeader } from '@/components/PageHeader';

import { useCurrentUser } from '@/store/useAppStore';
import { notify } from '@/store/useNotificationStore';

export function ExamResultPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const queryClient = useQueryClient();
  const user = useCurrentUser();

  // Состояния
  const [showAppealForm, setShowAppealForm] = useState(false);
  
  // A-4: Разделенный State
  const [studentAppealReason, setStudentAppealReason] = useState('');
  const [teacherVerdictComment, setTeacherVerdictComment] = useState('');
  
  const [editingAnswerId, setEditingId] = useState<string | null>(null);
  const [newScore, setNewScore] = useState<number>(0);
  const [teacherComment, setTeacherComment] = useState('');

  const isStaff = user?.role === 'teacher' || user?.role === 'admin' || user?.role === 'ta';

  // 1. Запросы
  const { data: result, isLoading: isResultLoading } = useQuery({
    queryKey: ['exam-result', sessionId],
    queryFn: () => getResult(sessionId!),
    refetchInterval: (q) => (q.state.data?.status !== 'completed' ? 3000 : false),
    enabled: !!sessionId,
  });

  const { data: session } = useQuery({
    queryKey: ['exam-session', sessionId],
    queryFn: () => getSession(sessionId!),
    enabled: !!sessionId,
    retry: false,
  });

  const { data: myAppeals } = useQuery({
    queryKey: ['my-appeals'],
    queryFn: getMyAppeals,
    enabled: !isStaff && !!sessionId,
  });

  const { data: teacherAppeals } = useQuery({
    queryKey: ['teacher-appeals'],
    queryFn: getAllAppeals,
    enabled: isStaff && !!sessionId,
  });

  const existingAppeal = isStaff 
    ? teacherAppeals?.find(a => a.sessionId === sessionId)
    : myAppeals?.find(a => a.sessionId === sessionId);

  const pendingAppealForTeacher = isStaff && existingAppeal?.status === 'pending' ? existingAppeal : null;

  // 2. Мутации
  const appealMutation = useMutation({
    mutationFn: () => submitAppeal({ sessionId: sessionId!, reason: studentAppealReason }),
    onSuccess: () => {
      notify('success', 'Апелляция отправлена');
      setShowAppealForm(false);
      setStudentAppealReason('');
      queryClient.invalidateQueries({ queryKey: ['my-appeals'] });
    },
  });

  const correctMutation = useMutation({
    mutationFn: (answerId: string) =>
      correctAnswer({ answerId, newScore: newScore / 100, teacherComment }),
    onSuccess: () => {
      notify('success', 'Оценка обновлена');
      setEditingId(null);
      queryClient.invalidateQueries({ queryKey: ['exam-result', sessionId] });
    },
  });

  const resolveMutation = useMutation({
    mutationFn: (status: 'accepted' | 'rejected') =>
      resolveAppeal(pendingAppealForTeacher!.id, {
        status,
        teacherComment: teacherVerdictComment || 'Обработано преподавателем',
      }),
    onSuccess: () => {
      notify('success', 'Апелляция закрыта');
      queryClient.invalidateQueries({ queryKey: ['teacher-appeals'] });
      setTeacherVerdictComment('');
    },
  });

  if (isResultLoading) return (
    <div className="flex flex-col items-center justify-center h-screen gap-4">
      <div className="h-12 w-12 border-4 border-primary border-t-transparent rounded-full animate-spin" />
      <p className="text-xs font-bold text-muted-app uppercase tracking-widest">Анализ работы...</p>
    </div>
  );

  if (!result) return null;

  const isProcessing = result.status !== 'completed' || !result.answers;
  const totalScorePct = result.totalScore !== null ? Math.round(result.totalScore * 100) : 0;

  return (
    <div className="min-h-full bg-app/20 flex flex-col pb-20">
      <PageHeader
        title="Разбор результатов"
        subtitle={isProcessing ? 'ИИ анализирует ответы...' : 'Экзамен завершен'}
        backTo={isStaff ? '/teacher/dashboard' : '/lectures'}
      />

      <main className="max-w-4xl mx-auto p-8 w-full space-y-10">

        {/* ── АНОМАЛИИ ── */}
        {isStaff && session?.isSuspicious && (
          <div className="bg-destructive/10 border-2 border-destructive/20 p-6 rounded-[2rem] flex items-center gap-6">
            <ShieldAlert size={32} className="text-destructive" />
            <div>
              <h3 className="text-destructive font-black uppercase text-lg">Внимание: Аномалия</h3>
              <p className="text-destructive/80 text-sm">Выявлено высокое сходство с источниками.</p>
            </div>
          </div>
        )}

        {/* ── БЛОК АПЕЛЛЯЦИИ ДЛЯ УЧИТЕЛЯ ── */}
        {pendingAppealForTeacher && (
          <section className="bg-warning/5 border-2 border-warning/20 p-8 rounded-[2rem] animate-in slide-in-from-left-4">
            <div className="flex items-start gap-4">
              <div className="bg-warning text-white p-3 rounded-2xl shadow-lg"><MessageSquare size={24} /></div>
              <div className="flex-1">
                <h3 className="text-lg font-black text-app uppercase">Открыта апелляция</h3>
                <p className="text-sm text-muted-app mt-1 font-medium italic">«{pendingAppealForTeacher.reason}»</p>
                <div className="mt-6 space-y-4">
                  <textarea
                    placeholder="Ваш вердикт студенту..."
                    className="w-full bg-surface border border-app rounded-xl p-4 text-sm outline-none focus:border-warning"
                    value={teacherVerdictComment}
                    onChange={(e) => setTeacherVerdictComment(e.target.value)}
                  />
                  <div className="flex gap-3">
                    <button onClick={() => resolveMutation.mutate('rejected')} disabled={!teacherVerdictComment} className="px-6 py-2 bg-app border border-app text-destructive font-bold text-xs rounded-xl disabled:opacity-50">ОТКЛОНИТЬ</button>
                    <button onClick={() => resolveMutation.mutate('accepted')} disabled={!teacherVerdictComment} className="px-6 py-2 bg-success text-white font-bold text-xs rounded-xl disabled:opacity-50">ПРИНЯТЬ</button>
                  </div>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* ── ИТОГОВЫЙ БАЛЛ ── */}
        <section className="bg-surface border border-app rounded-[2.5rem] p-10 shadow-sm text-center">
          <div className="flex flex-col items-center">
            <div className={clsx(
              "w-32 h-32 rounded-full border-8 flex items-center justify-center text-3xl font-black mb-6 shadow-xl",
              totalScorePct > 70 ? "border-success/20 text-success bg-success/5" :
                totalScorePct > 40 ? "border-warning/20 text-warning bg-warning/5" : "border-destructive/20 text-destructive bg-destructive/5"
            )}>
              {totalScorePct}%
            </div>
            <h2 className="text-3xl font-black text-app">Итоговый результат</h2>
            
            {!isStaff && !existingAppeal && !isProcessing && (
              <button onClick={() => setShowAppealForm(true)} className="mt-8 px-6 py-3 bg-primary/5 text-primary rounded-2xl text-[11px] font-black uppercase border border-primary/20">Оспорить результат</button>
            )}

            {showAppealForm && (
              <div className="mt-8 w-full max-w-lg">
                <textarea 
                  className="w-full border border-app rounded-2xl p-5 text-sm" 
                  placeholder="Ваши аргументы..." 
                  value={studentAppealReason}
                  onChange={(e) => setStudentAppealReason(e.target.value)} 
                />
                <div className="flex justify-end gap-3 mt-4">
                  <button onClick={() => setShowAppealForm(false)} className="text-xs font-bold text-muted-app">ОТМЕНА</button>
                  <button onClick={() => appealMutation.mutate()} disabled={appealMutation.isPending || !studentAppealReason} className="bg-primary text-white px-8 py-3 rounded-xl text-xs font-black disabled:opacity-50">ОТПРАВИТЬ</button>
                </div>
              </div>
            )}
          </div>
        </section>

        {/* ── ОТВЕТЫ ── */}
        <div className="space-y-6">
          {isProcessing ? (
            // Если ответов еще нет, показываем красивую заглушку вместо падения
            <div className="bg-surface border border-app rounded-[2rem] p-20 text-center">
              <div className="h-12 w-12 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />
              <p className="text-app font-bold">ИИ оценивает вашу работу</p>
              <p className="text-xs text-muted-app mt-1">Обычно это занимает от 10 до 30 секунд. Страница обновится автоматически.</p>
            </div>
          ) : (
            result.answers.map((answer, idx) => {
            const questionData = session?.questions.find((q) => q.id === answer.questionId);
            
            // B-2: Обработка null (когда оценка еще не рассчитана)
            const score = answer.finalScore !== null ? Math.round(answer.finalScore * 100) : null;
            const isEditing = editingAnswerId === answer.id;

            return (
              <div key={answer.id} className="bg-surface border border-app rounded-[2rem] overflow-hidden shadow-sm">
                <div className="p-6 border-b border-app bg-app/10 flex justify-between items-start">
                  <div className="flex-1">
                    <span className="text-[10px] font-black text-primary uppercase bg-primary/10 px-2 py-0.5 rounded">Вопрос {idx + 1}</span>
                    <h4 className="font-bold text-app mt-3">{questionData?.questionText || 'Текст вопроса недоступен'}</h4>
                  </div>
                  <div className={clsx(
                    "px-4 py-2 rounded-xl text-sm font-black flex items-center gap-2",
                    score === null ? "bg-surface-alt text-muted-app border border-app" :
                    score > 70 ? "bg-success text-white" : 
                    score > 40 ? "bg-warning text-white" : "bg-destructive text-white"
                  )}>
                    {score !== null ? `${score}%` : '—'}
                    
                    {/* A-5: Очистка teacherComment при старте редактирования */}
                    {isStaff && !isEditing && score !== null && (
                      <button onClick={() => { setEditingId(answer.id); setNewScore(score); setTeacherComment(''); }}>
                        <Edit3 size={14} />
                      </button>
                    )}
                  </div>
                </div>

                <div className="p-8 space-y-6">
                  {isEditing && (
                    <div className="bg-primary/5 border border-primary/20 p-6 rounded-2xl space-y-4">
                      <div className="flex justify-between text-xs font-bold text-primary"><span>Скорректировать балл:</span><span>{newScore}%</span></div>
                      <input type="range" min="0" max="100" className="w-full h-1.5 accent-primary" value={newScore} onChange={(e) => setNewScore(parseInt(e.target.value))} />
                      <textarea placeholder="Почему вы меняете оценку?" className="w-full bg-surface border border-app rounded-xl p-3 text-sm" value={teacherComment} onChange={(e) => setTeacherComment(e.target.value)} />
                      <div className="flex justify-end gap-2"><button onClick={() => setEditingId(null)} className="text-xs font-bold p-2 text-muted-app">ОТМЕНА</button><button onClick={() => correctMutation.mutate(answer.id)} className="bg-primary text-white px-4 py-2 rounded-lg text-xs font-black">СОХРАНИТЬ</button></div>
                    </div>
                  )}
                  <div>
                    <p className="text-[10px] font-black text-muted-app uppercase mb-3">Ответ студента</p>
                    <div className="p-5 bg-app/30 border border-app rounded-2xl text-sm italic">{answer.answerText || 'Пусто'}</div>
                  </div>
                  {answer.aiExplanation && (
                    <div className="flex gap-4 p-5 bg-primary/5 border border-primary/10 rounded-2xl">
                      <BrainCircuit size={20} className="text-primary shrink-0" />
                      <p className="text-sm font-medium">{answer.aiExplanation}</p>
                    </div>
                  )}
                  {/* РЕК#4: Эталонный ответ — показываем после сдачи */}
                  {answer.referenceAnswer && (
                    <details className="group">
                      <summary className="cursor-pointer text-[10px] font-black text-muted-app uppercase tracking-widest flex items-center gap-2 select-none hover:text-app transition-colors">
                        <span className="group-open:rotate-90 transition-transform inline-block">▶</span>
                        Эталонный ответ
                      </summary>
                      <div className="mt-3 p-5 bg-success/5 border border-success/20 rounded-2xl text-sm text-app leading-relaxed">
                        {answer.referenceAnswer}
                      </div>
                    </details>
                  )}
                </div>
              </div>
            );
          }))}
        </div>
      </main>
    </div>
  );
}