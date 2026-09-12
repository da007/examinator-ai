import { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { getSubjects } from '@/api/subject';
import { uploadLecture } from '@/api/lecture';
import { Upload, FileText, AlertCircle, Loader2, ChevronLeft, Calendar, Clock, Timer } from 'lucide-react';
import { notify } from '@/store/useNotificationStore';
import { PageHeader } from '@/components/PageHeader';
import { clsx } from 'clsx';
import { getApiErrorMessage } from '@/api/client';

// ─── helpers ──────────────────────────────────────────────────────────────────

/** Конвертирует значение datetime-local input в ISO UTC строку */
function localInputToISO(value: string): string | null {
  if (!value) return null;
  return new Date(value).toISOString();
}

/** Форматирует минуты в «Xч Yмин» для превью */
function formatDuration(mins: number): string {
  if (!mins || mins <= 0) return "";
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  if (h === 0) return `${m} мин`;
  if (m === 0) return `${h} ч`;
  return `${h} ч ${m} мин`;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function UploadPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [selectedSubjectId, setSelectedSubjectId] = useState('');
  const [isDragging, setIsDragging] = useState(false);

  // FIX-7: поля расписания
  const [openFrom, setOpenFrom] = useState('');
  const [deadlineAt, setDeadlineAt] = useState('');
  const [durationMinutes, setDurationMinutes] = useState('');

  const { data: subjects, isLoading: isLoadingSubjects, isError } = useQuery({
    queryKey: ['subjects'],
    queryFn: getSubjects,
  });

  useEffect(() => {
    if (subjects && subjects.length > 0 && !selectedSubjectId) {
      setSelectedSubjectId(subjects[0].id);
    }
  }, [subjects, selectedSubjectId]);

  const uploadMutation = useMutation({
    mutationFn: () =>
      uploadLecture(
        title,
        selectedSubjectId,
        file!,
        localInputToISO(openFrom),
        localInputToISO(deadlineAt),
        durationMinutes ? Number(durationMinutes) : null,
      ),
    onSuccess: () => {
      notify('success', 'Лекция успешно загружена и отправлена на анализ');
      navigate('/teacher/dashboard');
    },
    onError: (error: unknown) => {
      notify('error', getApiErrorMessage(error));
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) validateAndSetFile(e.target.files[0]);
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(e.type === 'dragenter' || e.type === 'dragover');
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files?.[0]) validateAndSetFile(e.dataTransfer.files[0]);
  };

  const validateAndSetFile = (f: File) => {
    const ext = f.name.split('.').pop()?.toLowerCase();
    if (ext !== 'docx' && ext !== 'txt') {
      notify('error', 'Поддерживаются только форматы .docx и .txt');
      return;
    }
    if (f.size > 10 * 1024 * 1024) {
      notify('error', 'Файл слишком большой (максимум 10 MB)');
      return;
    }
    setFile(f);
  };

  // Дедлайн не может быть раньше openFrom
  const minDeadline = openFrom || undefined;
  // duration должен быть целым числом > 0
  const durationNum = durationMinutes ? Number(durationMinutes) : null;
  const durationValid = durationMinutes === '' || (durationNum !== null && durationNum > 0 && Number.isInteger(durationNum));

  const isReady =
    title.length >= 3 &&
    selectedSubjectId !== '' &&
    file !== null &&
    durationValid &&
    !uploadMutation.isPending;

  return (
    <div className="min-h-full bg-app/20 flex flex-col">
      <PageHeader
        title="Новый материал"
        subtitle="Загрузите лекцию — ИИ подготовит вопросы для проверки знаний"
        backTo="/teacher/dashboard"
      />

      <main className="max-w-2xl mx-auto p-8 w-full animate-in fade-in slide-in-from-bottom-4 duration-500">
        {isError ? (
          <div className="bg-destructive/10 border border-destructive/20 p-6 rounded-2xl text-center">
            <AlertCircle className="text-destructive mx-auto mb-3" size={32} />
            <p className="text-sm font-bold text-app">Ошибка загрузки дисциплин</p>
            <p className="text-xs text-muted-app mt-1">Проверьте соединение с сервером</p>
          </div>
        ) : subjects && subjects.length === 0 ? (
          <div className="bg-warning/10 border border-warning/20 p-8 rounded-3xl text-center">
            <AlertCircle className="text-warning mx-auto mb-4" size={40} />
            <h3 className="text-lg font-black text-app">Нет доступных дисциплин</h3>
            <p className="text-sm text-muted-app mt-2 leading-relaxed">
              Администратор ещё не добавил ни одного предмета.
            </p>
            <button
              onClick={() => navigate('/teacher/dashboard')}
              className="mt-6 flex items-center gap-2 mx-auto text-xs font-bold text-primary uppercase"
            >
              <ChevronLeft size={14} /> Вернуться назад
            </button>
          </div>
        ) : (
          <div className="bg-surface border border-app rounded-[2.5rem] p-10 shadow-sm space-y-10">

            {/* ── Название ──────────────────────────────────────────── */}
            <div className="space-y-3">
              <label className="text-[10px] font-black uppercase tracking-widest text-muted-app ml-1">
                Название лекции
              </label>
              <input
                className="w-full bg-surface-alt border border-app rounded-2xl px-5 py-4 outline-none focus:border-primary focus:bg-surface transition-all font-medium text-app placeholder:text-muted-app/40"
                placeholder="Например: Основы квантовой механики"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </div>

            {/* ── Дисциплина ────────────────────────────────────────── */}
            <div className="space-y-3">
              <label className="text-[10px] font-black uppercase tracking-widest text-muted-app ml-1">
                Дисциплина
              </label>
              {isLoadingSubjects ? (
                <div className="flex items-center gap-3 px-5 py-4 bg-app/30 rounded-2xl">
                  <Loader2 size={16} className="animate-spin text-primary" />
                  <span className="text-xs font-bold text-muted-app uppercase">Получение списка...</span>
                </div>
              ) : (
                <select
                  className="w-full bg-surface-alt border border-app rounded-2xl px-5 py-4 outline-none focus:border-primary focus:bg-surface transition-all font-bold text-sm text-app appearance-none cursor-pointer"
                  value={selectedSubjectId}
                  onChange={(e) => setSelectedSubjectId(e.target.value)}
                >
                  {subjects?.map((s) => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
              )}
            </div>

            {/* ── Расписание экзамена ───────────────────────────────── */}
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Calendar size={14} className="text-muted-app" />
                <span className="text-[10px] font-black uppercase tracking-widest text-muted-app">
                  Расписание экзамена
                </span>
                <span className="text-[9px] text-muted-app/50 font-medium">(необязательно)</span>
              </div>

              <div className="grid grid-cols-2 gap-4">
                {/* Открытие */}
                <div className="space-y-2">
                  <label className="text-[10px] font-bold text-muted-app/70 uppercase tracking-wider flex items-center gap-1.5">
                    <Clock size={11} /> Открыть с
                  </label>
                  <input
                    type="datetime-local"
                    className="w-full bg-surface-alt border border-app rounded-2xl px-4 py-3 text-sm text-app outline-none focus:border-primary transition-all font-medium"
                    value={openFrom}
                    onChange={(e) => setOpenFrom(e.target.value)}
                  />
                </div>

                {/* Дедлайн */}
                <div className="space-y-2">
                  <label className="text-[10px] font-bold text-muted-app/70 uppercase tracking-wider flex items-center gap-1.5">
                    <AlertCircle size={11} /> Сдать до
                  </label>
                  <input
                    type="datetime-local"
                    min={minDeadline}
                    className={clsx(
                      "w-full bg-surface-alt border rounded-2xl px-4 py-3 text-sm text-app outline-none focus:border-primary transition-all font-medium",
                      deadlineAt && openFrom && deadlineAt < openFrom
                        ? "border-destructive/50 bg-destructive/5"
                        : "border-app"
                    )}
                    value={deadlineAt}
                    onChange={(e) => setDeadlineAt(e.target.value)}
                  />
                  {deadlineAt && openFrom && deadlineAt < openFrom && (
                    <p className="text-[10px] text-destructive font-bold">Дедлайн раньше открытия</p>
                  )}
                </div>
              </div>

              {/* Длительность */}
              <div className="space-y-2">
                <label className="text-[10px] font-bold text-muted-app/70 uppercase tracking-wider flex items-center gap-1.5">
                  <Timer size={11} /> Время на выполнение (минуты)
                </label>
                <div className="flex items-center gap-4">
                  <input
                    type="number"
                    min={1}
                    max={480}
                    placeholder="Например: 90"
                    className={clsx(
                      "flex-1 bg-surface-alt border rounded-2xl px-4 py-3 text-sm text-app outline-none focus:border-primary transition-all font-medium placeholder:text-muted-app/40",
                      !durationValid ? "border-destructive/50 bg-destructive/5" : "border-app"
                    )}
                    value={durationMinutes}
                    onChange={(e) => setDurationMinutes(e.target.value)}
                  />
                  {durationNum && durationNum > 0 && (
                    <span className="text-sm font-black text-primary whitespace-nowrap shrink-0">
                      = {formatDuration(durationNum)}
                    </span>
                  )}
                </div>
                {!durationValid && (
                  <p className="text-[10px] text-destructive font-bold">Введите целое число &gt; 0</p>
                )}
                <p className="text-[10px] text-muted-app/50">
                  Таймер начнётся с момента старта экзамена студентом. Без значения — без ограничений.
                </p>
              </div>
            </div>

            {/* ── Загрузка файла ────────────────────────────────────── */}
            <div className="space-y-3">
              <label className="text-[10px] font-black uppercase tracking-widest text-muted-app ml-1">
                Документ (DOCX или TXT)
              </label>
              <label
                className={clsx(
                  "group relative flex flex-col items-center justify-center w-full h-52 border-2 border-dashed rounded-[2rem] cursor-pointer transition-all duration-300",
                  isDragging
                    ? "border-primary bg-primary/10 scale-[1.02]"
                    : file
                    ? "border-success/40 bg-success/5 shadow-inner"
                    : "border-app hover:border-primary/40 bg-app/30 hover:bg-app/50"
                )}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
              >
                <div className="flex flex-col items-center justify-center pt-5 pb-6 text-center px-4 pointer-events-none">
                  {isDragging ? (
                    <>
                      <div className="w-14 h-14 bg-primary/20 text-primary rounded-2xl flex items-center justify-center mb-4 animate-bounce">
                        <Upload size={28} />
                      </div>
                      <p className="text-sm font-black text-primary uppercase">Бросайте файл сюда</p>
                    </>
                  ) : file ? (
                    <>
                      <div className="w-14 h-14 bg-success/20 text-success rounded-2xl flex items-center justify-center mb-4 shadow-lg shadow-success/10">
                        <FileText size={28} />
                      </div>
                      <p className="text-sm font-bold text-app truncate max-w-[240px]">{file.name}</p>
                      <p className="text-[10px] text-success font-black uppercase mt-2 tracking-tighter">
                        Файл готов к обработке
                      </p>
                    </>
                  ) : (
                    <>
                      <div className="w-14 h-14 bg-app text-muted-app group-hover:text-primary rounded-2xl flex items-center justify-center mb-4 transition-colors">
                        <Upload size={28} />
                      </div>
                      <p className="text-sm font-bold text-app">Выберите или перетащите файл</p>
                      <p className="text-[10px] text-muted-app mt-2 uppercase font-black tracking-widest opacity-60">
                        DOCX, TXT до 10 MB
                      </p>
                    </>
                  )}
                </div>
                <input
                  type="file"
                  className="hidden"
                  accept=".docx,.txt"
                  onChange={handleFileChange}
                  disabled={uploadMutation.isPending}
                />
              </label>
            </div>

            {/* ── Кнопка ────────────────────────────────────────────── */}
            <button
              onClick={() => uploadMutation.mutate()}
              disabled={!isReady}
              className="w-full bg-primary text-white py-5 rounded-2xl font-black text-sm flex items-center justify-center gap-3 hover:bg-primary-hover disabled:opacity-30 disabled:cursor-not-allowed transition-all shadow-xl shadow-primary/20 active:scale-[0.98]"
            >
              {uploadMutation.isPending ? (
                <>
                  <Loader2 className="animate-spin" size={20} />
                  <span>АНАЛИЗИРУЕМ ТЕКСТ...</span>
                </>
              ) : (
                <>
                  <FileText size={20} />
                  <span>НАЧАТЬ ГЕНЕРАЦИЮ ВОПРОСОВ</span>
                </>
              )}
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
