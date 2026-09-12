import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getLectures, deleteLecture, updateLecture, downloadLectureFile, regenerateLecture } from '@/api/lecture';
import { 
  Download, Trash2, Edit2, 
  Search, Clock, Save, X, Calendar, CalendarClock, Play, BarChart2,
  RefreshCw // <--- ДОБАВИТЬ ЭТУ ИКОНКУ
} from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { StatusStepIndicator } from '@/components/StatusStepIndicator';
import { notify } from '@/store/useNotificationStore';
import { clsx } from 'clsx';
import type { LectureRead } from '@/types';
import { useNavigate } from 'react-router-dom';
import { ConfirmDialog } from '@/components/ConfirmDialog';

function utcToLocalInputValue(utcString: string | null): string {
  if (!utcString) return '';
  const d = new Date(utcString);
  const offset = d.getTimezoneOffset() * 60000;
  return new Date(d.getTime() - offset).toISOString().substring(0, 16);
}

export function TeacherLecturesPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');

  // Состояния редактирования
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [editOpenFrom, setEditOpenFrom] = useState('');
  const [editDeadline, setEditDeadline] = useState('');
  const [confirmDialog, setConfirmDialog] = useState<{
    open: boolean;
    title: string;
    description?: string;
    onConfirm: () => void;
  }>({ open: false, title: '', onConfirm: () => {} });

  // 1. Загрузка списка с динамическим интервалом (Polling)
  const { data: lectures, isLoading } = useQuery({
    queryKey: ['lectures-management'],
    queryFn: getLectures,
    refetchInterval: (query) =>
      query.state.data?.some(l => ['processing', 'generating'].includes(l.status)) ? 5000 : 30000,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteLecture(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lectures-management'] });
      queryClient.invalidateQueries({ queryKey: ['lectures'] }); // A-3
      notify('success', 'Лекция полностью удалена');
    },
    onError: () => notify('error', 'Не удалось удалить лекцию'),
  });

  const updateMutation = useMutation({
    mutationFn: (payload: { id: string; title: string; openFrom?: string | null; deadlineAt?: string | null }) =>
      updateLecture(payload.id, {
        title: payload.title,
        openFrom: payload.openFrom ? new Date(payload.openFrom).toISOString() : null,
        deadlineAt: payload.deadlineAt ? new Date(payload.deadlineAt).toISOString() : null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lectures-management'] });
      queryClient.invalidateQueries({ queryKey: ['lectures'] }); // A-3
      setEditingId(null);
      notify('success', 'Параметры лекции обновлены');
    },
    onError: () => notify('error', 'Ошибка обновления лекции'),
  });

  const regenerateMutation = useMutation({
    mutationFn: (id: string) => regenerateLecture(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lectures-management'] });
      queryClient.invalidateQueries({ queryKey: ['lectures'] }); // A-3
      notify('success', 'Процесс перегенерации запущен');
    },
    onError: () => notify('error', 'Не удалось запустить регенерацию'),
  });

  const startEditing = (lecture: LectureRead) => {
    setEditingId(lecture.id);
    setEditTitle(lecture.title);
    setEditOpenFrom(utcToLocalInputValue(lecture.openFrom));
    setEditDeadline(utcToLocalInputValue(lecture.deadlineAt));
  };

  const filteredLectures = lectures?.filter(l =>
    l.title.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="min-h-full bg-app/20 flex flex-col">
      <PageHeader
        title="Управление лекциями"
        subtitle="Редактирование, дедлайны и аналитика по лекциям"
        actions={
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-app" size={16} />
            <input
              className="bg-surface border border-app rounded-xl pl-9 pr-4 py-2 text-sm outline-none focus:border-primary transition-all w-64"
              placeholder="Поиск лекций..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        }
      />

      <main className="max-w-5xl mx-auto p-8 w-full space-y-4">
        {isLoading ? (
          <div className="py-20 text-center animate-pulse text-muted-app">Загрузка лекций...</div>
        ) : !filteredLectures?.length ? (
          <div className="py-20 text-center text-muted-app text-sm italic">Лекции не найдены</div>
        ) : (
          filteredLectures.map((lecture) => (
            <div key={lecture.id} className="bg-surface border border-app rounded-2xl p-6 shadow-sm space-y-4">

              {/* ── ЗАГОЛОВОК ── */}
              {editingId === lecture.id ? (
                <div className="space-y-3">
                  <input
                    className="w-full bg-app border border-app rounded-xl px-4 py-2.5 text-sm font-bold outline-none focus:border-primary"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    placeholder="Название лекции"
                  />
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-[10px] font-bold uppercase text-muted-app mb-1 flex items-center gap-1">
                        <Calendar size={10} /> Открыть с
                      </label>
                      <input
                        type="datetime-local"
                        className="w-full bg-app border border-app rounded-lg px-3 py-2 text-xs outline-none focus:border-primary"
                        value={editOpenFrom}
                        onChange={(e) => setEditOpenFrom(e.target.value)}
                      />
                    </div>
                    <div>
                      <label className="text-[10px] font-bold uppercase text-muted-app mb-1 flex items-center gap-1">
                        <CalendarClock size={10} /> Дедлайн
                      </label>
                      <input
                        type="datetime-local"
                        className="w-full bg-app border border-app rounded-lg px-3 py-2 text-xs outline-none focus:border-primary"
                        value={editDeadline}
                        onChange={(e) => setEditDeadline(e.target.value)}
                      />
                    </div>
                  </div>
                  <div className="flex gap-2 justify-end">
                    <button onClick={() => setEditingId(null)} className="p-2 text-muted-app hover:text-app"><X size={16} /></button>
                    <button
                      onClick={() => updateMutation.mutate({ id: lecture.id, title: editTitle, openFrom: editOpenFrom || null, deadlineAt: editDeadline || null })}
                      disabled={updateMutation.isPending}
                      className="flex items-center gap-2 bg-primary text-white px-4 py-2 rounded-lg text-xs font-bold"
                    >
                      <Save size={14} /> {updateMutation.isPending ? 'Сохранение...' : 'Сохранить'}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-bold text-app text-base truncate">{lecture.title}</h3>
                    <div className="flex items-center gap-3 mt-1 text-[10px] text-muted-app font-mono">
                      <span className="flex items-center gap-1"><Clock size={10} /> {new Date(lecture.createdAt).toLocaleDateString()}</span>
                      {lecture.openFrom && <span className="flex items-center gap-1"><Calendar size={10} /> С {new Date(lecture.openFrom).toLocaleDateString()}</span>}
                      {lecture.deadlineAt && <span className="flex items-center gap-1"><CalendarClock size={10} /> До {new Date(lecture.deadlineAt).toLocaleDateString()}</span>}
                    </div>
                  </div>

                  {/* ── КНОПКИ ДЕЙСТВИЙ ── */}
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {/* ИСПРАВЛЕНО: кнопка аналитики теперь передаёт lectureId в URL */}
                    {lecture.status === 'published' && (
                      <button
                        onClick={() => navigate(`/teacher/analytics/${lecture.id}`)}
                        className="p-2 text-muted-app hover:text-primary hover:bg-primary/10 rounded-lg transition-colors"
                        title="Аналитика"
                      >
                        <BarChart2 size={16} />
                      </button>
                    )}
                    {(lecture.status === 'review_required') && (
                      <button
                        onClick={() => navigate(`/teacher/moderation/${lecture.id}`)}
                        className="flex items-center gap-1 bg-primary text-white px-3 py-1.5 rounded-lg text-[10px] font-black shadow-lg shadow-primary/20"
                      >
                        <Play size={10} /> МОДЕРАЦИЯ
                      </button>
                    )}
					<button
					  onClick={() => setConfirmDialog({
              open: true,
              title: 'Перегенерировать вопросы?',
              description: 'Все текущие вопросы и чанки будут удалены.',
              onConfirm: () => { regenerateMutation.mutate(lecture.id); setConfirmDialog(d => ({ ...d, open: false })); },
            })}
					  disabled={regenerateMutation.isPending || ['processing', 'generating'].includes(lecture.status)}
					  className="p-2 text-muted-app hover:text-warning hover:bg-warning/10 rounded-lg transition-colors disabled:opacity-30"
					  title="Перегенерировать вопросы"
					>
					  <RefreshCw size={16} className={clsx(regenerateMutation.isPending && "animate-spin")} />
</button>
                    <button
                      onClick={() => downloadLectureFile(lecture.id, `${lecture.title}.pdf`)}
                      className="p-2 text-muted-app hover:text-app hover:bg-app/50 rounded-lg transition-colors"
                      title="Скачать файл"
                    >
                      <Download size={16} />
                    </button>
                    <button
                      onClick={() => startEditing(lecture)}
                      className="p-2 text-muted-app hover:text-primary hover:bg-primary/10 rounded-lg transition-colors"
                      title="Редактировать"
                    >
                      <Edit2 size={16} />
                    </button>
                    <button
                      onClick={() => setConfirmDialog({
                        open: true,
                        title: `Удалить лекцию "${lecture.title}"?`,
                        description: 'Это действие необратимо.',
                        onConfirm: () => { deleteMutation.mutate(lecture.id); setConfirmDialog(d => ({ ...d, open: false })); },
                      })}
                      disabled={deleteMutation.isPending}
                      className="p-2 text-muted-app hover:text-destructive hover:bg-destructive/10 rounded-lg transition-colors disabled:opacity-30"
                      title="Удалить"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              )}

              {/* ── СТАТУС ОБРАБОТКИ ── */}
              {['processing', 'generating', 'review_required'].includes(lecture.status) && (
                <div className="bg-app/30 rounded-2xl p-3 border border-app">
                  <StatusStepIndicator status={lecture.status} />
                </div>
              )}
            </div>
          ))
        )}
      </main>
      <ConfirmDialog
        open={confirmDialog.open}
        title={confirmDialog.title}
        description={confirmDialog.description}
        onConfirm={confirmDialog.onConfirm}
        onCancel={() => setConfirmDialog(d => ({ ...d, open: false }))}
      />
    </div>
  );
}