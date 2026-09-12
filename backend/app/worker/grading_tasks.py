import asyncio
import logging
import uuid
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.celery_app import celery
from app.db.session import get_session_maker, get_engine
from app.models.exam import ExamSession, StudentAnswer, SessionStatus
from app.services.ai.grading_service import grading_service

logger = logging.getLogger(__name__)

async def _grade_exam_session_logic(session_id: str):
    """
    Логика оценки сессии. 
    Исправлено: обработка awaitable объектов и корректная подгрузка связей.
    """
    async with get_session_maker()() as db:
        # 1. Загружаем сессию и все ответы с вопросами
        # Используем joinedload для минимизации SQL-запросов (N+1 problem)
        query = (
            select(ExamSession)
            .where(ExamSession.id == uuid.UUID(session_id))
            .options(
                joinedload(ExamSession.answers)
                .joinedload(StudentAnswer.question)
            )
        )
        result = await db.execute(query)
        
        # .unique() обязателен при joinedload в 2.0, чтобы не было дублей строк сессии
        session = result.unique().scalar_one_or_none()

        if not session:
            logger.error(f"Session {session_id} not found for grading")
            return

        if session.status != SessionStatus.PROCESSING:
            logger.warning(f"Session {session_id} is in status {session.status}, skipping grading")
            return

        logger.info(f"Starting HGC grading for session {session_id}")

        total_conf = 0.0
        valid_answers = 0

        for answer in session.answers:
            try:
                # Вызов Hybrid Grading Core (Layer 1-4)
                # Исправление: гарантируем корректный вызов асинхронного метода
                evaluation = await grading_service.evaluate_answer(
                    question=answer.question,
                    answer_text=answer.answer_text,
                    formula_data=answer.formula_data
                )

                # Сохраняем результаты
                answer.final_score = evaluation.get("final_score", 0.0)
                answer.confidence_score = evaluation.get("confidence_score", 0.0)
                answer.ai_score = evaluation.get("metrics", {})
                
                similarity = evaluation.get("metrics", {}).get("similarity", 0)
                if similarity > 0.95:
                     # Слишком близко к эталону — возможно Copy-Paste из лекции
                     answer.is_plagiarism = True
                
                # Если ИИ не уверен (Confidence < 60%), помечаем для учителя
                if answer.confidence_score < 0.6:
                    answer.manual_review_required = True
                
                total_conf += answer.confidence_score
                valid_answers += 1

            except Exception as e:
                logger.error(f"Error grading answer {answer.id}: {str(e)}", exc_info=True)
                answer.final_score = 0.0
                answer.ai_score = {"error": "Internal grading error", "details": str(e)}
                answer.manual_review_required = True

        plagiarism_count = sum(1 for a in session.answers if a.is_plagiarism)
        if plagiarism_count / len(session.answers) > 0.3:
            session.is_suspicious = True
            session.integrity_details = {"reason": "High similarity with source material in multiple answers"}

        # 2. Обновляем статус сессии
        session.status = SessionStatus.COMPLETED
        
        try:
            await db.commit()
            avg_conf = total_conf / valid_answers if valid_answers > 0 else 0
            logger.info(f"Grading finished for {session_id}. Avg Confidence: {avg_conf:.2f}")
        except Exception as commit_err:
            logger.error(f"Failed to commit grades for session {session_id}: {commit_err}")
            await db.rollback()

async def _run_grading_with_cleanup(session_id: str):
    """Гарантированное освобождение ресурсов после выполнения задачи."""
    try:
        await _grade_exam_session_logic(session_id)
    finally:
        await get_engine().dispose()

@celery.task(name="grade_exam_session_task", bind=True, max_retries=3)
def grade_exam_session_task(self, session_id: str):
    """Celery-задача для оценки экзаменационной работы."""
    try:
        # Используем asyncio.run, так как воркер работает в синхронном контексте
        return asyncio.run(_run_grading_with_cleanup(session_id))
    except Exception as exc:
        logger.warning(f"Retrying grading task for {session_id} due to: {exc}")
        # Повтор через 60 секунд при временных сбоях (например, таймаут LLM)
        raise self.retry(exc=exc, countdown=60)

async def _recalculate_question_logic(question_id: str):
    """
    Логика массового пересчета баллов для всех студентов по конкретному вопросу.
    """
    async with get_session_maker()() as db:
        # 1. Получаем вопрос и все ответы на него
        q_uuid = uuid.UUID(question_id)
        question_query = select(Question).where(Question.id == q_uuid)
        q_res = await db.execute(question_query)
        question = q_res.scalar_one_or_none()

        if not question:
            logger.error(f"Question {question_id} not found for recalculation")
            return

        # Ищем все ответы студентов на этот вопрос
        answers_query = select(StudentAnswer).where(StudentAnswer.question_id == q_uuid)
        ans_res = await db.execute(answers_query)
        answers = ans_res.scalars().all()

        logger.info(f"Recalculating {len(answers)} answers for question {question_id}")

        for answer in answers:
            # ПРОПУСКАЕМ, если преподаватель УЖЕ внес ручную правку (приоритет человека)
            if answer.ai_score and "audit" in answer.ai_score:
                # Если в аудите есть запись от teacher, не трогаем
                if any(entry.get("teacher_id") for entry in answer.ai_score["audit"]):
                    continue

            try:
                # Повторный прогон через HGC
                evaluation = await grading_service.evaluate_answer(
                    question=question,
                    answer_text=answer.answer_text,
                    formula_data=answer.formula_data
                )

                # Обновляем данные
                answer.final_score = evaluation.get("final_score", 0.0)
                answer.confidence_score = evaluation.get("confidence_score", 0.0)
                
                # Помечаем в метаданных, что это был системный пересчет
                new_metrics = evaluation.get("metrics", {})
                new_metrics["recalculated_at"] = datetime.now(timezone.utc).isoformat()
                answer.ai_score = new_metrics

                if answer.confidence_score < 0.6:
                    answer.manual_review_required = True
                else:
                    answer.manual_review_required = False

            except Exception as e:
                logger.error(f"Failed to recalculate answer {answer.id}: {e}")

        await db.commit()
        logger.info(f"Mass recalculation finished for question {question_id}")

@celery.task(name="recalculate_scores_for_question_task")
def recalculate_scores_for_question_task(question_id: str):
    """Точка входа Celery для массового пересчета."""
    return asyncio.run(_recalculate_question_logic(question_id))