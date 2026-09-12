import uuid
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import StreamingResponse

from app.api import dependencies
from app.models.user import User, UserRole
from app.schemas.analytics import TeacherDashboard, LectureAnalytics, StudentProgress

from app.models.subject import Subject
from app.services.analytics_service import analytics_service

router = APIRouter()

@router.get("/dashboard", response_model=TeacherDashboard)
async def get_teacher_dashboard(
    db: AsyncSession = Depends(dependencies.get_db),
    current_user: User = Depends(dependencies.RoleChecker([UserRole.TEACHER, UserRole.ADMIN])),
) -> Any:
    """
    Получение сводных данных для главного экрана преподавателя.
    Включает счетчики студентов, активных лекций и задач на проверку.
    """
    return await analytics_service.get_teacher_dashboard(db, org_id=current_user.org_id)

@router.get("/lecture/{lecture_id}", response_model=LectureAnalytics)
async def get_lecture_analytics(
    lecture_id: uuid.UUID,
    db: AsyncSession = Depends(dependencies.get_db),
    current_user: User = Depends(dependencies.RoleChecker([UserRole.TEACHER, UserRole.ADMIN])),
) -> Any:
    """
    Детальная аналитика по конкретной лекции: распределение оценок и метрики ИИ.
    """
    stats = await analytics_service.get_lecture_analytics(
        db, lecture_id=lecture_id, org_id=current_user.org_id
    )
    if not stats:
        raise HTTPException(status_code=404, detail="Аналитика для данной лекции не найдена")
    return stats

@router.get("/student/me", response_model=StudentProgress)
async def get_my_progress(
    db: AsyncSession = Depends(dependencies.get_db),
    current_user: User = Depends(dependencies.get_current_user),
) -> Any:
    """
    Личная аналитика студента: средний балл и динамика по темам.
    """
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=400, detail="Только для студентов")
    
    # Здесь вызывается метод агрегации для студента (реализуется аналогично в analytics_service)
    # Для MVP возвращаем структуру на основе данных пользователя
    from sqlalchemy import select, func
    from app.models.exam import StudentAnswer, ExamSession
    
    # Агрегированные метрики студента (только завершённые, только проверенные ответы)
    query = (
        select(func.avg(StudentAnswer.final_score), func.count(func.distinct(ExamSession.id)))
        .join(ExamSession, StudentAnswer.session_id == ExamSession.id)
        .where(
            ExamSession.student_id == current_user.id,
            ExamSession.status == "completed",
            StudentAnswer.final_score.is_not(None),
        )
    )
    res = await db.execute(query)
    row = res.one()
    avg_score_raw, total_completed = row[0], row[1] or 0

    # Безопасное преобразование None/NaN → 0
    try:
        avg_score = round(float(avg_score_raw), 2) if avg_score_raw is not None else 0.0
    except (TypeError, ValueError):
        avg_score = 0.0

    # История баллов: последние 10 сессий в хронологическом порядке
    history_q = (
        select(func.avg(StudentAnswer.final_score))
        .join(ExamSession, StudentAnswer.session_id == ExamSession.id)
        .where(
            ExamSession.student_id == current_user.id,
            ExamSession.status == "completed",
            StudentAnswer.final_score.is_not(None),
        )
        .group_by(ExamSession.id, ExamSession.start_time)
        .order_by(ExamSession.start_time.desc())
        .limit(10)
    )
    history_res = await db.execute(history_q)
    score_history = [
        round(float(r[0]), 2) for r in history_res.all() if r[0] is not None
    ][::-1]

    return StudentProgress(
        avg_score=avg_score,
        exams_completed=total_completed,
        strong_topics=[],
        weak_topics=[],
        score_history=score_history,
    )

@router.get("/subjects/{subject_id}/export")
async def export_grades(
    subject_id: uuid.UUID,
    db: AsyncSession = Depends(dependencies.get_db),
    current_user: User = Depends(dependencies.RoleChecker([UserRole.TEACHER, UserRole.ADMIN])),
):
    """
    Скачать ведомость по дисциплине в формате XLSX.
    """
    subject = await db.get(Subject, subject_id)
    if not subject or subject.org_id != current_user.org_id:
        raise HTTPException(status_code=404, detail="Дисциплина не найдена")

    file_buffer = await analytics_service.export_subject_grades(
        db, subject_id=subject_id, org_id=current_user.org_id
    )
    
    filename = f"Grades_{subject.name.replace(' ', '_')}.xlsx"
    encoded_filename = quote(filename)
    
    return StreamingResponse(
        file_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            # Используем стандарт filename*=utf-8'' для кириллицы
            "Content-Disposition": f"attachment; filename*=utf-8''{encoded_filename}"
        }
    )