from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth, 
    lectures, 
    questions, 
    exams, 
    reviews,
    analytics,
    subjects 
)

# Создаем главный роутер для версии V1
api_router = APIRouter()

# Подключаем роутер аутентификации
api_router.include_router(
    auth.router, 
    prefix="/auth", 
    tags=["auth"]
)

# Роутер управления лекциями (Teacher/Admin)
api_router.include_router(
    lectures.router,
    prefix="/lectures",
    tags=["lectures"]
)

# Роутер управления вопросами (Teacher/Admin)
api_router.include_router(
    questions.router,
    prefix="/questions",
    tags=["questions"]
)

# Роутер прохождения тестов (Student)
api_router.include_router(
    exams.router,
    prefix="/exams",
    tags=["exams"]
)

# [NEW] Роутер ручной проверки и апелляций (Teacher/Student)
api_router.include_router(
    reviews.router,
    prefix="/reviews",
    tags=["reviews"]
)

# [NEW] Роутер аналитики и отчетности (Teacher/Student)
api_router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["analytics"]
)

# Роутер управления дисциплинами
api_router.include_router(
    subjects.router,
    prefix="/subjects",
    tags=["subjects"]
)