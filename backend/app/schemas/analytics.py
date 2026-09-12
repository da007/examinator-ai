import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import Field
from app.schemas.base import APIModel


class AIQualityMetrics(APIModel):
    """Метрики качества работы HGC (Hybrid Grading Core)."""
    avg_confidence: float = Field(..., description="Средняя уверенность ИИ в оценках")
    manual_review_rate: float = Field(..., description="Доля ответов, ушедших на ручную проверку")
    appeal_rate: float = Field(..., description="Процент апелляций от общего числа работ")
    ai_accuracy_estimate: float = Field(..., description="Оценочная точность (сопоставление ИИ и правок учителя)")


class GradeDistribution(APIModel):
    """Распределение оценок для построения гистограммы."""
    bins: List[str] = Field(default=["0-20%", "20-40%", "40-60%", "60-80%", "80-100%"])
    counts: List[int] = Field(..., description="Количество работ в каждом диапазоне")


class TopicMastery(APIModel):
    """
    Данные для Concept Mastery Heatmap (Task 3.2).
    Показывает, насколько хорошо группа освоила конкретный фрагмент (чанк) лекции.
    """
    chunk_id: Any
    topic_name: str = Field(..., description="Краткое содержание или заголовок темы")
    avg_score: float = Field(..., description="Средний балл группы по этой теме (0.0 - 1.0)")
    student_count: int = Field(..., description="Количество студентов, ответивших на вопросы по этой теме")


class KillerQuestion(APIModel):
    """
    Данные для блока 'Вопросы-убийцы' (Task 3.4).
    Вопросы с аномально низким процентом успеха.
    """
    question_id: Any
    question_text: str
    success_rate: float = Field(..., description="Доля правильных ответов (score > 0.7)")

class StudentAttendance(APIModel):
    """Статус прохождения лекции конкретным студентом."""
    student_id: uuid.UUID
    session_id: Optional[uuid.UUID] = None 
    student_name: str
    student_email: str
    status: str = Field(..., description="'not_started', 'active', 'completed'")
    score: Optional[float] = None
    last_activity: Optional[datetime] = None
    is_suspicious: bool = False


class LectureAnalytics(APIModel):
    """Детальная аналитика по конкретной лекции для Профессорского дашборда."""
    lecture_id: Any
    lecture_title: str
    total_exams: int = Field(..., description="Всего завершенных попыток")
    avg_score: float = Field(..., description="Средний балл по всей лекции")
    
    attendance: List[StudentAttendance] = []
    
    # Визуальные компоненты
    grade_distribution: GradeDistribution
    topic_mastery: List[TopicMastery] = []
    killer_questions: List[KillerQuestion] = []
    ai_metrics: AIQualityMetrics
    
    # Мониторинг честности (Task 3.3)
    suspicious_sessions_count: int = Field(0, description="Количество работ с флагом is_suspicious")


class TeacherDashboard(APIModel):
    """Сводные данные главного экрана преподавателя (University Edition)."""
    total_students: int
    active_subjects: int = Field(..., description="Количество активных дисциплин")
    active_lectures: int = Field(..., description="Количество опубликованных лекций")
    
    # Очередь задач
    pending_reviews_count: int = Field(..., description="Требуют ручной проверки (Low Confidence)")
    pending_appeals_count: int = Field(..., description="Нерассмотренные апелляции")
    
    # Новое: флаги честности на главном экране
    total_suspicious_count: int = Field(0, description="Всего подозрительных сессий в организации")
    
    recent_activity: List[Dict[str, Any]] = Field(default=[], description="Последние 5 завершенных работ")


class StudentProgress(APIModel):
    """Личная аналитика студента."""
    avg_score: float
    exams_completed: int
    # Темы на основе TopicMastery, где балл > 0.8 или < 0.4
    strong_topics: List[str] = []
    weak_topics: List[str] = []
    
    # Динамика (последние оценки)
    score_history: List[float] = []