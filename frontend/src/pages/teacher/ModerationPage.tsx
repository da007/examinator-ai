import { useState } from 'react';
import { PageHeader } from '@/components/PageHeader';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getQuestionsByLecture, updateQuestion, deleteQuestion, createQuestion } from '@/api/question';
import { publishLecture } from '@/api/lecture';
import { Save, Trash2, Plus, CheckCircle2} from 'lucide-react';
import { notify } from '@/store/useNotificationStore';

export function ModerationPage() {
  const { lectureId } = useParams<{ lectureId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient(); // Добавили доступ к клиенту

  const { data: questions, isLoading } = useQuery({
    queryKey: ['moderation-questions', lectureId],
    queryFn: () => getQuestionsByLecture(lectureId!),
    enabled: !!lectureId
  });

  // НОВАЯ МУТАЦИЯ СОЗДАНИЯ
  const createMutation = useMutation({
    mutationFn: () => createQuestion(lectureId!, {
      questionText: "Новый вопрос",
      referenceAnswer: "Введите эталонный ответ",
      keyTheses: [],
      difficulty: "medium",
      questionType: "open_ended"
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['moderation-questions', lectureId] });
    }
  });


  
  const publishMutation = useMutation({
    mutationFn: () => publishLecture(lectureId!),
    onSuccess: () => navigate('/teacher/lectures') // Изменено на список лекций
  });

  if (isLoading) return <div className="p-12 text-center animate-pulse">Загрузка вопросов...</div>;

  const hasInvalidQuestions = questions?.some(
    (q) => !q.questionText?.trim() || !q.referenceAnswer?.trim() || q.referenceAnswer.trim().length < 10
  ) ?? false;

  const canPublish = !!questions?.length && !hasInvalidQuestions && !publishMutation.isPending;

  return (
    <div className="min-h-screen bg-app text-app p-8">
      <div className="max-w-4xl mx-auto">
        <PageHeader
          title="Модерация вопросов"
          subtitle="Проверка и редактирование сгенерированного контента"
          backTo="/teacher/lectures"
          sticky={false}
          actions={
            <div className="flex gap-3">
              <button
                onClick={() => createMutation.mutate()}
                disabled={createMutation.isPending}
                className="flex items-center gap-2 px-5 py-2.5 bg-app border border-app rounded-xl text-xs font-bold hover:bg-surface-alt transition-all"
              >
                <Plus size={16} /> ДОБАВИТЬ ВОПРОС
              </button>
              
              <button
                disabled={!canPublish}
                onClick={() => {
                  if (hasInvalidQuestions) {
                    notify('warning', 'Все вопросы должны иметь текст и эталонный ответ (мин. 10 символов)');
                    return;
                  }
                  publishMutation.mutate();
                }}
                className="bg-success text-white px-6 py-2.5 rounded-xl text-xs font-black flex items-center gap-2 hover:opacity-90 disabled:opacity-50 shadow-lg shadow-success/20 transition-all"
              >
                <CheckCircle2 size={16} /> ОПУБЛИКОВАТЬ
              </button>
            </div>
          }
        />
        <div className="mt-8" /> {/* Отступ после хедера */}

        <div className="space-y-6">
          {questions?.map((q) => (
            <QuestionEditorItem key={q.id} question={q} lectureId={lectureId!} />
          ))}
        </div>
      </div>
    </div>
  );
}

// ✅ ИСПРАВЛЕНО: lectureId передаётся как проп, чтобы queryClient.invalidateQueries
// мог использовать точный ключ ['moderation-questions', lectureId].
// useQueryClient() вызывается ВНУТРИ компонента — это легальный вызов хука.
function QuestionEditorItem({ question, lectureId }: { question: any; lectureId: string }) {
  const [formData, setFormData] = useState(question);
  // ✅ ИСПРАВЛЕНО: хук объявлен в правильном scope — внутри функционального компонента
  const queryClient = useQueryClient();

  const updateMutation = useMutation({
    mutationFn: () => updateQuestion(question.id, formData),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['moderation-questions', lectureId] })
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteQuestion(question.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['moderation-questions', lectureId] })
  });

  return (
    <div className="bg-surface border border-app rounded-xl p-6 shadow-sm space-y-4">
      <div className="flex justify-between gap-4">
        <textarea 
          className="flex-1 bg-app border border-app rounded p-3 text-sm font-medium outline-none focus:border-primary"
          value={formData.questionText}
          onChange={e => setFormData({...formData, questionText: e.target.value})}
          placeholder="Текст вопроса"
        />
        <button onClick={() => deleteMutation.mutate()} className="text-destructive p-2 hover:bg-destructive/10 rounded">
          <Trash2 size={18} />
        </button>
      </div>

      <div className="space-y-2">
        <label className="text-[10px] font-bold uppercase text-muted-app">Эталонный ответ</label>
        <textarea 
          className="w-full bg-app border border-app rounded p-3 text-sm outline-none focus:border-primary"
          rows={3}
          value={formData.referenceAnswer}
          onChange={e => setFormData({...formData, referenceAnswer: e.target.value})}
        />
      </div>

      <div className="space-y-2">
        <div className="flex justify-between items-center">
          <label className="text-[10px] font-bold uppercase text-muted-app">Ключевые тезисы (для оценки ИИ)</label>
          <button 
            onClick={() => setFormData({...formData, keyTheses: [...formData.keyTheses, {text: '', importance: 2}]})}
            className="text-primary text-[10px] font-bold hover:underline flex items-center gap-1"
          >
            <Plus size={12} /> ДОБАВИТЬ
          </button>
        </div>
        <div className="grid gap-2">
          {formData.keyTheses.map((t: any, idx: number) => (
            <div key={idx} className="flex gap-2">
              <input 
                className="flex-1 bg-surface-alt border border-app rounded px-3 py-1.5 text-xs"
                value={t.text}
                onChange={e => {
                  const newTheses = [...formData.keyTheses];
                  newTheses[idx].text = e.target.value;
                  setFormData({...formData, keyTheses: newTheses});
                }}
              />
              <select 
                className="bg-surface-alt border border-app rounded px-2 text-[10px]"
                value={t.importance}
                onChange={e => {
                  const newTheses = [...formData.keyTheses];
                  newTheses[idx].importance = Number(e.target.value);
                  setFormData({...formData, keyTheses: newTheses});
                }}
              >
                <option value={1}>Low</option>
                <option value={2}>Mid</option>
                <option value={3}>High</option>
              </select>
            </div>
          ))}
        </div>
      </div>

      <div className="pt-4 border-t border-app flex justify-end">
        <button 
          onClick={() => updateMutation.mutate()}
          disabled={updateMutation.isPending}
          className="bg-primary text-white px-4 py-1.5 rounded text-xs font-bold flex items-center gap-2"
        >
          <Save size={14} /> {updateMutation.isPending ? 'СОХРАНЕНИЕ...' : 'СОХРАНИТЬ ИЗМЕНЕНИЯ'}
        </button>
      </div>
    </div>
  );
}
