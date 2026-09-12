import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy import select, func, and_, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
import pandas as pd
import io
from fastapi.responses import StreamingResponse

from app.models.exam import ExamSession, StudentAnswer, SessionStatus
from app.models.appeal import StudentAppeal, AppealStatus
from app.models.question import Question
from app.models.chunk import Chunk
from app.models.lecture import Lecture
from app.models.user import User, UserRole
from app.models.subject import Subject
from app.schemas.analytics import (
    TeacherDashboard, 
    AIQualityMetrics, 
    LectureAnalytics, 
    GradeDistribution,
    StudentAttendance,
    TopicMastery,
    KillerQuestion
)

class AnalyticsService:
    """
    Сервис агрегации метрик.
    Исправлено: добавлена защита от пустых результатов (NPE) и улучшена подгрузка связей.
    """

    async def get_teacher_dashboard(
        self, db: AsyncSession, *, org_id: uuid.UUID
    ) -> TeacherDashboard:
        """Сводная информация для дашборда преподавателя."""
        from sqlalchemy import or_ # Локальный импорт для безопасности

        # 1. Базовые счетчики
        total_students_query = select(func.count(User.id)).where(
            and_(User.org_id == org_id, User.role == UserRole.STUDENT)
        )
        total_students = await db.scalar(total_students_query) or 0
        
        active_lectures_query = select(func.count(Lecture.id)).where(
            and_(Lecture.org_id == org_id, Lecture.status == "published")
        )
        active_lectures = await db.scalar(active_lectures_query) or 0

        active_subjects_query = select(func.count(Subject.id)).where(
            Subject.org_id == org_id
        )
        active_subjects = await db.scalar(active_subjects_query) or 0
        
        # 2. Очередь проверки (Уникальные сессии с низким доверием ИИ или подозрением на плагиат)
        pending_reviews_query = (
            select(func.count(func.distinct(ExamSession.id)))
            .join(StudentAnswer, StudentAnswer.session_id == ExamSession.id, isouter=True)
            .join(Lecture, ExamSession.lecture_id == Lecture.id)
            .where(
                and_(
                    Lecture.org_id == org_id,
                    ExamSession.status == SessionStatus.COMPLETED,
                    or_(
                        StudentAnswer.manual_review_required == True,
                        ExamSession.is_suspicious == True
                    )
                )
            )
        )
        pending_reviews = await db.scalar(pending_reviews_query) or 0

        # 3. Апелляции (ФИКС: Определение пропущенной переменной)
        pending_appeals_query = (
            select(func.count(StudentAppeal.id))
            .join(ExamSession, StudentAppeal.session_id == ExamSession.id)
            .join(Lecture, ExamSession.lecture_id == Lecture.id)
            .where(
                and_(
                    Lecture.org_id == org_id, 
                    StudentAppeal.status == AppealStatus.PENDING
                )
            )
        )
        pending_appeals = await db.scalar(pending_appeals_query) or 0

        # 4. Общий счетчик аномалий для виджета
        total_suspicious_query = (
            select(func.count(ExamSession.id))
            .join(Lecture, ExamSession.lecture_id == Lecture.id)
            .where(and_(Lecture.org_id == org_id, ExamSession.is_suspicious == True))
        )
        total_suspicious = await db.scalar(total_suspicious_query) or 0

        # 5. Недавняя активность (5 последних работ)
        recent_query = (
            select(ExamSession)
            .join(Lecture, ExamSession.lecture_id == Lecture.id)
            .where(and_(Lecture.org_id == org_id, ExamSession.status == SessionStatus.COMPLETED))
            .options(joinedload(ExamSession.lecture))
            .order_by(desc(ExamSession.updated_at))
            .limit(5)
        )
        recent_res = await db.execute(recent_query)
        recent_sessions = recent_res.scalars().unique().all()

        recent_activity = []
        for s in recent_sessions:
            recent_activity.append({
                "session_id": str(s.id),
                "lecture_title": s.lecture.title if s.lecture else "Удаленная лекция",
                "student_id": str(s.student_id),
                "date": s.updated_at.isoformat()
            })

        return TeacherDashboard(
            total_students=total_students,
            active_subjects=active_subjects,
            active_lectures=active_lectures,
            pending_reviews_count=pending_reviews,
            pending_appeals_count=pending_appeals,
            total_suspicious_count=total_suspicious,
            recent_activity=recent_activity
        )

    async def export_subject_grades(
        self, db: AsyncSession, *, subject_id: uuid.UUID, org_id: uuid.UUID
    ) -> io.BytesIO:
        """
        Генерация Excel-ведомости по дисциплине.
        Колонки: Студент, Лекция 1, Лекция 2, ..., Средний балл.
        """
        # 1. Получаем все опубликованные лекции этой дисциплины
        lectures_query = (
            select(Lecture)
            .where(and_(Lecture.subject_id == subject_id, Lecture.status == "published"))
            .order_by(Lecture.created_at)
        )
        l_res = await db.execute(lectures_query)
        lectures = l_res.scalars().all()
        lecture_titles = [l.title for l in lectures]

        # 2. Получаем все результаты студентов этой организации по этим лекциям
        # Берем MAX балл, если студент проходил тест несколько раз
        session_scores_subq = (
            select(
                ExamSession.student_id,
                ExamSession.lecture_id,
                func.avg(StudentAnswer.final_score).label("session_avg")
            )
            .join(StudentAnswer, StudentAnswer.session_id == ExamSession.id)
            .where(ExamSession.status == SessionStatus.COMPLETED)
            .group_by(ExamSession.id)
            .subquery()
        )

        # Затем берем лучший балл сессии для каждого студента
        results_query = (
            select(
                User.full_name,
                User.email,
                Lecture.title.label("lecture_title"),
                func.max(session_scores_subq.c.session_avg).label("best_score")
            )
            .join(session_scores_subq, User.id == session_scores_subq.c.student_id)
            .join(Lecture, session_scores_subq.c.lecture_id == Lecture.id)
            .where(and_(
                Lecture.subject_id == subject_id,
                User.org_id == org_id
            ))
            .group_by(User.id, Lecture.id)
        )
        r_res = await db.execute(results_query)
        rows = r_res.all()
        r_res = await db.execute(results_query)
        rows = r_res.all()

        # 3. Формируем DataFrame через Pandas
        if not rows:
            # Если данных нет, создаем пустую таблицу с заголовками
            df = pd.DataFrame(columns=["ФИО Студента", "Email"] + lecture_titles)
        else:
            # Превращаем в плоский список словарей
            data = []
            for r in rows:
                data.append({
                    "ФИО Студента": r.full_name or "Не указано",
                    "Email": r.email,
                    "lecture": r.lecture_title,
                    "score": round(float(r.best_score) * 100, 1) # В процентах 0-100
                })
            
            df_raw = pd.DataFrame(data)
            # Pivot table: превращаем строки лекций в колонки
            df = df_raw.pivot(
                index=["ФИО Студента", "Email"], 
                columns="lecture", 
                values="score"
            ).reset_index()
            
            # Добавляем колонку среднего балла
            score_cols = [c for c in df.columns if c not in ["ФИО Студента", "Email"]]
            df["Итоговый прогресс (%)"] = df[score_cols].mean(axis=1).round(1)

        # 4. Запись в буфер байтов (без сохранения на диск)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Ведомость')
        
        output.seek(0)
        return output

    async def get_lecture_analytics(
        self, db: AsyncSession, *, lecture_id: uuid.UUID, org_id: uuid.UUID
    ) -> Optional[LectureAnalytics]:
        lecture = await db.get(Lecture, lecture_id)
        if not lecture or (lecture.org_id != org_id):
            return None

        # 1. Сводные метрики по сессиям
        # Считаем только завершенные сессии для статистики оценок
        stats_query = (
            select(
                func.count(func.distinct(ExamSession.id)).label("cnt"), # <--- ИСПРАВЛЕНО
                func.avg(StudentAnswer.final_score).label("avg"),
                func.avg(StudentAnswer.confidence_score).label("avg_conf")
            )
            .join(StudentAnswer, StudentAnswer.session_id == ExamSession.id)
            .where(and_(ExamSession.lecture_id == lecture_id, ExamSession.status == SessionStatus.COMPLETED))
        )
        res = await db.execute(stats_query)
        base_stats = res.mappings().first()

        if not base_stats or base_stats["cnt"] == 0:
            # Если никто еще не сдал, возвращаем пустую структуру, но с Attendance
            return await self._get_empty_analytics_with_attendance(db, lecture)

        # 2. Распределение оценок (Buckets)
        dist_query = (
            select(
                func.count(ExamSession.id).label("count"),
                func.floor(func.least(func.avg(StudentAnswer.final_score), 0.99) * 5).label("bucket")
            )
            .join(StudentAnswer)
            .where(ExamSession.lecture_id == lecture_id)
            .group_by(ExamSession.id) # Группируем по сессии чтобы получить средний балл работы
        )
        # Оборачиваем в подзапрос для итогового распределения
        sub = dist_query.subquery()
        final_dist_query = select(sub.c.bucket, func.count().label("total")).group_by(sub.c.bucket)
        
        dist_res = await db.execute(final_dist_query)
        counts = [0] * 5
        for row in dist_res.all():
            if row.bucket is not None:
                idx = int(row.bucket)
                counts[idx] = row.total

        # 3. Список студентов (Attendance)
        students_res = await db.execute(select(User).where(and_(User.org_id == org_id, User.role == UserRole.STUDENT, User.is_active == True)))
        all_students = students_res.scalars().all()

        sessions_res = await db.execute(select(ExamSession).where(ExamSession.lecture_id == lecture_id).options(joinedload(ExamSession.answers)))
        all_sessions = {s.student_id: s for s in sessions_res.scalars().unique().all()}

        attendance_list = []
        for student in all_students:
            session = all_sessions.get(student.id)
            
            # Расчет оценки только если сессия завершена
            student_score = None
            if session and session.status == SessionStatus.COMPLETED and session.answers:
                valid_scores = [a.final_score for a in session.answers if a.final_score is not None]
                if valid_scores:
                    student_score = sum(valid_scores) / len(valid_scores)

            attendance_list.append(StudentAttendance(
                student_id=student.id,
                session_id=session.id if session else None, # <--- ТЕПЕРЬ ПЕРЕДАЕМ ID
                student_name=student.full_name or student.email,
                student_email=student.email,
                status=session.status if session else "not_started",
                score=student_score,
                last_activity=session.updated_at if session else None,
                is_suspicious=session.is_suspicious if session else False
            ))

        # 4. Расчет Killer Questions (Вопросы, где средний балл < 40%)
        # Мы берем вопросы этой лекции и считаем средний балл ответов на них
        killer_query = (
            select(
                Question.id,
                Question.question_text,
                func.avg(StudentAnswer.final_score).label("success_rate")
            )
            .join(StudentAnswer, StudentAnswer.question_id == Question.id)
            .join(Chunk, Question.chunk_id == Chunk.id)
            .where(Chunk.lecture_id == lecture_id)
            .group_by(Question.id)
            .having(and_(
                func.avg(StudentAnswer.final_score) < 0.4,
                func.count(StudentAnswer.id) >= 2
            ))
            .order_by("success_rate")
            .limit(5)
        )
        k_res = await db.execute(killer_query)
        killer_questions = [
            KillerQuestion(question_id=row.id, question_text=row.question_text, success_rate=float(row.success_rate))
            for row in k_res.all()
        ]

        # 5. Расчет Topic Mastery (Сложность тем по чанкам)
        topic_query = (
            select(
                Chunk.id,
                Chunk.text_content,
                func.avg(StudentAnswer.final_score).label("avg_chunk_score"),
                func.count(func.distinct(ExamSession.student_id)).label("students_count")
            )
            .join(Question, Question.chunk_id == Chunk.id)
            .join(StudentAnswer, StudentAnswer.question_id == Question.id)
            .join(ExamSession, StudentAnswer.session_id == ExamSession.id)
            .where(Chunk.lecture_id == lecture_id)
            .group_by(Chunk.id)
        )
        t_res = await db.execute(topic_query)
        topic_mastery = [
            TopicMastery(
                chunk_id=row.id,
                topic_name=row.text_content[:60] + "...", # Берем начало текста как название темы
                avg_score=float(row.avg_chunk_score),
                student_count=row.students_count
            )
            for row in t_res.all()
        ]

        # 6. Сборка итогового объекта (ОБНОВЛЕНО)
        return LectureAnalytics(
            lecture_id=lecture.id,
            lecture_title=lecture.title,
            total_exams=base_stats["cnt"],
            avg_score=float(base_stats["avg"]) if base_stats.get("avg") is not None else 0.0,
            grade_distribution=GradeDistribution(counts=counts),
            topic_mastery=topic_mastery,
            killer_questions=killer_questions,
            ai_metrics=AIQualityMetrics(
                avg_confidence=float(base_stats["avg_conf"] or 0),
                manual_review_rate=0.1, # В будущем считать на лету
                appeal_rate=0.05,
                ai_accuracy_estimate=0.95
            ),
            attendance=attendance_list,
            suspicious_sessions_count=0 # Пока заглушка
        )

    async def _get_empty_analytics_with_attendance(self, db, lecture) -> LectureAnalytics:
        # Вспомогательный метод для лекций без сданных работ
        students_res = await db.execute(select(User).where(and_(User.org_id == lecture.org_id, User.role == UserRole.STUDENT)))
        attendance = [StudentAttendance(
            student_id=s.id, student_name=s.full_name or s.email, student_email=s.email, status="not_started"
        ) for s in students_res.scalars().all()]

        return LectureAnalytics(
            lecture_id=lecture.id,
            lecture_title=lecture.title,
            total_exams=0,
            avg_score=0.0,
            grade_distribution=GradeDistribution(counts=[0,0,0,0,0]),
            ai_metrics=AIQualityMetrics(avg_confidence=0, manual_review_rate=0, appeal_rate=0, ai_accuracy_estimate=1),
            attendance=attendance
        )

analytics_service = AnalyticsService()