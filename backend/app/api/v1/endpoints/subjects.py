import uuid
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api import dependencies
from app.models.user import User, UserRole, UserRole
from app.models.subject import Subject
from app.schemas.subject import SubjectRead

router = APIRouter()

# Выносим проверку прав в отдельную переменную с валидным именем
checker_is_staff = dependencies.RoleChecker([UserRole.TEACHER, UserRole.ADMIN, UserRole.TA])

@router.get("/", response_model=List[SubjectRead])
async def read_subjects(
    db: AsyncSession = Depends(dependencies.get_db),
    current_user: User = Depends(dependencies.get_current_user), # <--- ТЕПЕРЬ СТУДЕНТ ТОЖЕ МОЖЕТ ЧИТАТЬ
) -> Any:
    """
    Получение списка всех дисциплин организации.
    Используется преподавателями для выбора при создании лекций.
    """
    from sqlalchemy.orm import joinedload
    query = (
        select(Subject)
        .options(joinedload(Subject.teacher)) # Подгружаем юзера-преподавателя
        .where(Subject.org_id == current_user.org_id)
        .order_by(Subject.name)
    )
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/{subject_id}", response_model=SubjectRead)
async def read_subject(
    subject_id: uuid.UUID,
    db: AsyncSession = Depends(dependencies.get_db),
    current_user: User = Depends(checker_is_staff),
) -> Any:
    """Детальная информация о конкретной дисциплине."""
    query = select(Subject).where(Subject.id == subject_id)
    result = await db.execute(query)
    subject = result.scalar_one_or_none()
    
    if not subject:
        raise HTTPException(status_code=404, detail="Дисциплина не найдена")
    
    if subject.org_id != current_user.org_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Доступ запрещен")
        
    return subject