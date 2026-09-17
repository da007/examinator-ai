import uuid
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import dependencies
from app.models.user import User, UserRole
from app.models.lecture import Lecture
from app.schemas.question import QuestionRead, QuestionUpdate
from app.services.question_service import question_service

router = APIRouter()

@router.get("/lecture/{lecture_id}", response_model=List[QuestionRead])
async def read_questions_by_lecture(
    lecture_id: uuid.UUID,
    db: AsyncSession = Depends(dependencies.get_db),
    current_user: User = Depends(dependencies.RoleChecker([UserRole.TEACHER, UserRole.ADMIN])),
) -> Any:
    """Получение всех вопросов лекции для модерации."""
    # Проверка прав (org_id) — внутри сервиса
    questions = await question_service.get_questions_by_lecture(
        db, lecture_id=lecture_id, org_id=current_user.org_id
    )
    return questions

@router.patch("/{question_id}", response_model=QuestionRead)
async def update_question(
    question_id: uuid.UUID,
    obj_in: QuestionUpdate,
    db: AsyncSession = Depends(dependencies.get_db),
    current_user: User = Depends(dependencies.RoleChecker([UserRole.TEACHER, UserRole.ADMIN])),
) -> Any:
    """Обновление вопроса."""
    # get_question_safe сразу фильтрует по org_id — чужой вопрос вернётся как None
    question = await question_service.get_question_safe(
        db, question_id=question_id, org_id=current_user.org_id
    )
    if not question:
        raise HTTPException(status_code=404, detail="Вопрос не найден")
    
    return await question_service.update_question(db, db_obj=question, obj_in=obj_in)

@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    question_id: uuid.UUID,
    db: AsyncSession = Depends(dependencies.get_db),
    current_user: User = Depends(dependencies.RoleChecker([UserRole.TEACHER, UserRole.ADMIN])),
):
    """Удаление вопроса. Возвращает пустой ответ со статусом 204."""
    question = await question_service.get_question_safe(
        db, question_id=question_id, org_id=current_user.org_id
    )
    if not question:
        raise HTTPException(status_code=404, detail="Вопрос не найден")
    
    await question_service.delete_question(db, question_id=question_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/{question_id}/recalculate", status_code=status.HTTP_202_ACCEPTED)
async def trigger_recalculation(
    question_id: uuid.UUID,
    db: AsyncSession = Depends(dependencies.get_db),
    current_user: User = Depends(dependencies.RoleChecker([UserRole.TEACHER, UserRole.ADMIN])),
) -> Any:
    """
    Запуск массового пересчета баллов студентов по данному вопросу.
    Используется, если преподаватель изменил эталонный ответ.
    """
    # Проверка прав (Multi-tenancy)
    question = await question_service.get_question_safe(
        db, question_id=question_id, org_id=current_user.org_id
    )
    if not question:
        raise HTTPException(status_code=404, detail="Вопрос не найден")

    # Запуск фоновой задачи — пересчёт идёт асинхронно, эндпоинт не ждёт результата
    from app.worker.grading_tasks import recalculate_scores_for_question_task
    recalculate_scores_for_question_task.delay(str(question_id))

    return {"message": "Процесс пересчета баллов запущен в фоновом режиме"}

@router.post("/lecture/{lecture_id}", response_model=QuestionRead)
async def create_manual_question(
    lecture_id: uuid.UUID,
    obj_in: QuestionUpdate,
    db: AsyncSession = Depends(dependencies.get_db),
    current_user: User = Depends(dependencies.RoleChecker([UserRole.TEACHER, UserRole.ADMIN])),
) -> Any:
    """Ручное создание вопроса для лекции."""
    # 0. Проверяем, что лекция существует и принадлежит организации пользователя
    lecture = await db.get(Lecture, lecture_id)
    if not lecture or (lecture.org_id != current_user.org_id and not current_user.is_superuser):
        raise HTTPException(status_code=404, detail="Лекция не найдена")

    # 1. Находим первый попавшийся чанк лекции, чтобы привязать вопрос (т.к. chunk_id обязателен в БД)
    from app.models.chunk import Chunk
    chunk_query = select(Chunk).where(Chunk.lecture_id == lecture_id).limit(1)
    chunk_res = await db.execute(chunk_query)
    chunk = chunk_res.scalar_one_or_none()
    
    if not chunk:
        raise HTTPException(status_code=400, detail="Невозможно добавить вопрос: лекция еще не обработана (нет чанков)")

    # 2. Создаем вопрос через сервис
    from app.schemas.question import QuestionCreate
    new_q_data = QuestionCreate(
        chunk_id=chunk.id,
        question_text=obj_in.question_text or "Новый вопрос",
        reference_answer=obj_in.reference_answer or "",
        key_theses=obj_in.key_theses or [],
        difficulty=obj_in.difficulty or "medium",
        question_type=obj_in.question_type or "open_ended"
    )
    
    from app.services.question_service import question_service
    return await question_service.create_question(db, obj_in=new_q_data)