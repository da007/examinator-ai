import { useParams, Navigate } from 'react-router-dom';
import { ExamEngine } from '@/features/exams/ExamEngine';

/**
 * Страница экзамена. 
 * Извлекает ID сессии из URL и передает его в оркестратор ExamEngine.
 * Обеспечивает изоляцию интерфейса экзамена от остальной части приложения.
 */
export function ExamPage() {
  const { sessionId } = useParams<{ sessionId: string }>();

  // Если вдруг ID отсутствует в URL, возвращаем пользователя на дашборд
  if (!sessionId) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="exam-page-container h-screen w-full bg-app overflow-hidden">
      {/* 
        Вся логика (транспорт, стейт, рендеринг чата/стандарта) 
        инкапсулирована внутри ExamEngine.
      */}
      <ExamEngine sessionId={sessionId} />
    </div>
  );
}