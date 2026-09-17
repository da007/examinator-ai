import uuid
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.api import dependencies
from app.models.user import User, UserRole, UserRole
from app.models.exam import ExamSession, SessionStatus
from app.models.question import Question
from app.models.lecture import Lecture, LectureStatus
from app.schemas.exam import (
    ExamSessionRead, 
    ExamSessionCreate, 
    ExamSessionUpdateDraft,
    ExamResultRead,
    StudentAnswerRead
)
from app.services.exam_service import exam_service

router = APIRouter()

@router.post("/start", response_model=ExamSessionRead)
async def start_exam(
    *,
    db: AsyncSession = Depends(dependencies.get_db),
    current_user: User = Depends(dependencies.get_current_user),
    obj_in: ExamSessionCreate
) -> Any:
    """
    Инициализация экзаменационной сессии. 
    Теперь возвращает вопросы сразу при старте.
    """
    # Один раз достаём лекцию в начале — используем её и для проверки доступа студента,
    # и для общей проверки статуса ниже (было: два отдельных db.get, один из них с багом)
    lec = await db.get(Lecture, obj_in.lecture_id)
    if not lec:
        raise HTTPException(status_code=404, detail="Лекция не найдена")

    # Проверка доступа актуальна только для студентов (преподаватель/админ ограничений не имеют)
    if current_user.role == UserRole.STUDENT:
        from app.models.group import group_students, group_subjects

        # Проверяем, привязана ли дисциплина хоть к каким-то группам вообще
        any_group_q = (
            select(group_subjects.c.subject_id)
            .where(group_subjects.c.subject_id == lec.subject_id)
            .limit(1)
        )
        subject_has_groups = (await db.execute(any_group_q)).scalar_one_or_none()

        if subject_has_groups:
            # Если дисциплина привязана к группам — доступ только у студентов из этих групп
            access_q = (
                select(group_students.c.student_id)
                .join(group_subjects, group_students.c.group_id == group_subjects.c.group_id)
                .where(
                    group_students.c.student_id == current_user.id,
                    group_subjects.c.subject_id == lec.subject_id,
                )
                .limit(1)
            )
            has_access = (await db.execute(access_q)).scalar_one_or_none()
            if not has_access:
                raise HTTPException(
                    status_code=403,
                    detail="Нет доступа к данной дисциплине. Обратитесь к преподавателю."
                )
        else:
            # Иначе (групп нет) — достаточно совпадения организации
            if lec.org_id != current_user.org_id:
                raise HTTPException(status_code=403, detail="Нет доступа к данной дисциплине")

    if lec.status != LectureStatus.PUBLISHED:
        raise HTTPException(
            status_code=403,
            detail="Лекция не опубликована или ещё обрабатывается"
        )

    # Создание сессии и генерация набора вопросов (логика в сервисе)
    session = await exam_service.start_session(db, student_id=current_user.id, obj_in=obj_in)
    
    # Подгружаем сами вопросы по id из сессии
    questions_query = select(Question).where(Question.id.in_(session.question_ids))
    q_result = await db.execute(questions_query)
    questions = q_result.scalars().all()
    
    # Восстанавливаем порядок вопросов, заданный в session.question_ids
    # (select IN не гарантирует порядок результатов)
    questions_map = {str(q.id): q for q in questions}
    sorted_questions = [questions_map[str(qid)] for qid in session.question_ids if str(qid) in questions_map]
    return ExamSessionRead(
        id=session.id,
        lecture_id=session.lecture_id,
        status=session.status,
        version=session.version,
        start_time=session.start_time,
        end_time=session.end_time,
        current_draft=session.current_draft,
        questions=sorted_questions
    )

@router.patch("/sessions/{session_id}/draft", response_model=ExamSessionRead)
async def save_draft(
    session_id: uuid.UUID,
    obj_in: ExamSessionUpdateDraft,
    db: AsyncSession = Depends(dependencies.get_db),
    current_user: User = Depends(dependencies.get_current_user),
) -> Any:
    """
    Автосохранение ответов (Debounce на фронтенде).
    Требует корректную версию для Optimistic Locking.
    """
    # Вся логика (проверка владельца, сверка version) — внутри сервиса
    return await exam_service.update_draft(
        db, session_id=session_id, student_id=current_user.id, obj_in=obj_in
    )

@router.post("/sessions/{session_id}/submit", response_model=ExamSessionRead)
async def submit_exam(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(dependencies.get_db),
    current_user: User = Depends(dependencies.get_current_user),
) -> Any:
    """
    Завершение теста и отправка на проверку ИИ.
    """
    return await exam_service.submit_session(
        db, session_id=session_id, student_id=current_user.id
    )

@router.get("/sessions/{session_id}/result", response_model=ExamResultRead)
async def get_exam_result(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(dependencies.get_db),
    current_user: User = Depends(dependencies.get_current_user),
) -> Any:
    """
    Получение результатов теста с прикреплением эталонных ответов.
    """
    from sqlalchemy.orm import joinedload
    from app.models.exam import StudentAnswer
    from app.models.lecture import Lecture

    # 1. Достаем сессию БЕЗ жесткого фильтра по student_id
    # (фильтр по владельцу делаем вручную ниже, чтобы разграничить права студента и преподавателя)
    query = (
        select(ExamSession)
        .where(ExamSession.id == session_id)
        .options(
            joinedload(ExamSession.answers).joinedload(StudentAnswer.question)
        )
    )
    result = await db.execute(query)
    session = result.unique().scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Результаты не найдены")
    
    # 2. ПРОВЕРКА ПРАВ ДОСТУПА
    if current_user.role == UserRole.STUDENT and not current_user.is_superuser:
        # Студент может смотреть только свои работы
        if session.student_id != current_user.id:
            # 404, а не 403 — чтобы не палить студенту сам факт существования чужой сессии
            raise HTTPException(status_code=404, detail="Результаты не найдены")
    else:
        # Преподаватель/Админ могут смотреть, если лекция из их организации
        lecture = await db.get(Lecture, session.lecture_id)
        if lecture and lecture.org_id != current_user.org_id and not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Доступ к данным другой организации запрещен")

    # 3. Проверка статуса проверки — пока ИИ считает баллы, результат ещё не готов
    if session.status == SessionStatus.PROCESSING:
        raise HTTPException(
            status_code=202, 
            detail="Ваша работа еще проверяется ИИ. Пожалуйста, подождите."
        )

    # 4. Рассчитываем суммарный балл — среднее по всем уже оцененным ответам
    # (ответы без final_score, например неотвеченные, не учитываются)
    valid_scores = [a.final_score for a in session.answers if a.final_score is not None]
    total_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0.0
    
    # 5. Формируем список ответов для ответа API, подтягивая эталонный ответ из вопроса
    answers_out = []
    for answer in session.answers:
        answers_out.append(StudentAnswerRead(
            id=answer.id,
            question_id=answer.question_id,
            answer_text=answer.answer_text,
            formula_data=answer.formula_data,
            final_score=answer.final_score,
            confidence_score=answer.confidence_score,
            ai_score=answer.ai_score, 
            reference_answer=answer.question.reference_answer if answer.question else None
        ))
    
    return ExamResultRead(
        session_id=session.id,
        status=session.status,
        total_score=total_score,
        answers=answers_out
    )

@router.get("/sessions", response_model=List[ExamSessionRead])
async def get_my_sessions(
    db: AsyncSession = Depends(dependencies.get_db),
    current_user: User = Depends(dependencies.get_current_user),
) -> Any:
    """Получение истории всех экзаменационных сессий текущего студента."""
    # Всегда фильтруем по текущему юзеру — эндпоинт возвращает только "свою" историю
    query = select(ExamSession).where(ExamSession.student_id == current_user.id).order_by(ExamSession.start_time.desc())
    result = await db.execute(query)
    sessions = result.scalars().all()
    
    return [
        ExamSessionRead(
            id=s.id,
            lecture_id=s.lecture_id,
            status=s.status,
            version=s.version,
            start_time=s.start_time,
            end_time=s.end_time,
            current_draft=s.current_draft,
            questions=[] # Для списка истории вопросы обычно не нужны
        ) for s in sessions
    ]

@router.get("/sessions/{session_id}", response_model=ExamSessionRead)
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(dependencies.get_db),
    current_user: User = Depends(dependencies.get_current_user),
) -> Any:
    """
    Получение данных сессии. Доступно студенту-владельцу или персоналу организации.
    """
    query = select(ExamSession).where(ExamSession.id == session_id)
    
    # Студенту сразу сужаем запрос до его собственных сессий (на уровне SQL)
    if current_user.role == UserRole.STUDENT and not current_user.is_superuser:
        query = query.where(ExamSession.student_id == current_user.id)
    
    result = await db.execute(query)
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")

    # Для не-студентов (преподаватель/админ) дополнительно проверяем принадлежность к организации
    if current_user.role != UserRole.STUDENT:
        from app.models.lecture import Lecture
        lecture = await db.get(Lecture, session.lecture_id)
        if lecture and lecture.org_id != current_user.org_id and not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Доступ к данным другой организации запрещен")

    # Подгружаем вопросы сессии и восстанавливаем их порядок (как и в /start)
    questions_query = select(Question).where(Question.id.in_(session.question_ids))
    q_result = await db.execute(questions_query)
    questions = q_result.scalars().all()
    
    questions_map = {str(q.id): q for q in questions}
    sorted_questions = [questions_map[str(qid)] for qid in session.question_ids if str(qid) in questions_map]

    return ExamSessionRead(
        id=session.id,
        lecture_id=session.lecture_id,
        status=session.status,
        version=session.version,
        start_time=session.start_time,
        end_time=session.end_time,
        current_draft=session.current_draft,
        questions=sorted_questions
    )