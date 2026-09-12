from app.models.user import User, UserRole
from app.models.subject import Subject
from app.models.lecture import Lecture, LectureStatus
from app.models.group import Group, group_students, group_subjects
from app.models.chunk import Chunk
from app.models.question import Question
from app.models.exam import ExamSession, StudentAnswer, SessionStatus
from app.models.appeal import StudentAppeal, AppealStatus

# Это позволяет делать 'from app.models import User, Lecture' и т.д.
__all__ = [
    "User",
    "UserRole",
    "Subject",
    "Lecture",
    "LectureStatus",
    "Group",
    "Chunk",
    "Question",
    "ExamSession",
    "StudentAnswer",
    "SessionStatus",
    "StudentAppeal",
    "AppealStatus",
]