import uuid
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from app.api import dependencies
from app.models.user import User, UserRole
from app.models.exam import ExamSession, SessionStatus
from app.models.appeal import StudentAppeal
from app.models.lecture import Lecture
from app.schemas.review import (
    AppealCreate, 
    AppealRead, 
    AppealResolve, 
    ManualAnswerCorrection,
    PendingReviewList
)
from app.schemas.exam import StudentAnswerRead
from app.services.review_service import review_service

router = APIRouter()

# --- ЭНДПОИНТЫ ПРЕПОДАВАТЕЛЯ ---

@router.get("/pending", response_model=List[PendingReviewList])
async def get_pending_reviews(
    db: AsyncSession = Depends(dependencies.get_db),
    current_user: User = Depends(dependencies.RoleChecker([UserRole.TEACHER, UserRole.ADMIN, UserRole.TA])),
) -> Any:
    """
    Получение списка сессий, требующих ручного вмешательства (низкий Confidence).
    Доступно только преподавателям данной организации.
    """
    sessions = await review_service.get_sessions_needing_review(
        db, org_id=current_user.org_id
    )
    
    # Маппинг в упрощенную схему для дашборда
    # (средняя уверенность модели по сессии — чтобы сортировать/приоритизировать проверку)
    return [
        PendingReviewList(
            session_id=s.id,
            student_name=s.student.full_name or "Unknown",
            lecture_title=s.lecture.title,
            avg_confidence=sum(a.confidence_score or 0 for a in s.answers) / len(s.answers) if s.answers else 0,
            created_at=s.created_at
        ) for s in sessions
    ]

@router.post("/correct-answer", response_model=StudentAnswerRead)
async def correct_student_answer(
    correction: ManualAnswerCorrection,
    db: AsyncSession = Depends(dependencies.get_db),
    current_user: User = Depends(dependencies.RoleChecker([UserRole.TEACHER, UserRole.ADMIN, UserRole.TA])),
) -> Any:
    """
    Ручное переопределение оценки ИИ преподавателем.
    """
    # Вся логика (проверка владения сессией, пересчёт итогового балла) — внутри сервиса
    return await review_service.correct_answer(
        db, correction=correction, teacher_id=current_user.id
    )

@router.patch("/appeals/{appeal_id}/resolve", response_model=AppealRead)
async def resolve_appeal(
    appeal_id: uuid.UUID,
    obj_in: AppealResolve,
    db: AsyncSession = Depends(dependencies.get_db),
    current_user: User = Depends(dependencies.RoleChecker([UserRole.TEACHER, UserRole.ADMIN, UserRole.TA])),
) -> Any:
    """
    Принятие или отклонение апелляции студента.
    """
    return await review_service.resolve_appeal(
        db, appeal_id=appeal_id, obj_in=obj_in, org_id=current_user.org_id
    )

# --- ЭНДПОИНТЫ СТУДЕНТА ---

@router.post("/appeals", response_model=AppealRead, status_code=status.HTTP_201_CREATED)
async def submit_appeal(
    obj_in: AppealCreate,
    db: AsyncSession = Depends(dependencies.get_db),
    current_user: User = Depends(dependencies.get_current_user),
) -> Any:
    """
    Подача апелляции студентом на результаты теста.
    """
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Только студенты могут подавать апелляции")
        
    return await review_service.create_appeal(
        db, student_id=current_user.id, obj_in=obj_in
    )

@router.get("/my-appeals", response_model=List[AppealRead])
async def get_my_appeals(
    db: AsyncSession = Depends(dependencies.get_db),
    current_user: User = Depends(dependencies.get_current_user),
) -> Any:
    """
    Просмотр студентом своих апелляций.
    """
    from sqlalchemy import select
    from app.models.appeal import StudentAppeal
    
    # Только апелляции текущего студента — фильтр по student_id
    query = select(StudentAppeal).where(StudentAppeal.student_id == current_user.id)
    result = await db.execute(query)
    return result.scalars().all()
    
@router.get("/appeals", response_model=List[AppealRead])
async def get_all_org_appeals(
    db: AsyncSession = Depends(dependencies.get_db),
    current_user: User = Depends(dependencies.RoleChecker([UserRole.TEACHER, UserRole.ADMIN, UserRole.TA])),
) -> Any:
    """Получение всех апелляций организации для преподавателя."""
    from app.models.appeal import StudentAppeal
    from app.models.lecture import Lecture
    from app.models.exam import ExamSession
    from sqlalchemy.orm import joinedload

    # 1. Запрос с подгрузкой студента (joinedload), чтобы не делать отдельный запрос
    # на каждого студента при формировании student_name/student_email ниже
    query = (
        select(StudentAppeal)
        .join(ExamSession, StudentAppeal.session_id == ExamSession.id)
        .join(Lecture, ExamSession.lecture_id == Lecture.id)
        .options(joinedload(StudentAppeal.student))
        .where(Lecture.org_id == current_user.org_id)
        .order_by(StudentAppeal.created_at.desc())
    )
    result = await db.execute(query)
    appeals = result.scalars().all()

    # 2. Мапим вручную, чтобы заполнить student_name и student_email
    # (эти поля есть в AppealRead, но их нет в самой модели StudentAppeal)
    return [
        AppealRead(
            **{c.name: getattr(a, c.name) for c in a.__table__.columns},
            student_name=a.student.full_name,
            student_email=a.student.email
        ) for a in appeals
    ]