import os
from celery import Celery
from app.core.config import settings

# Инициализируем Celery
celery = Celery("worker")

# Настраиваем Celery
celery.conf.update(
    broker_url=f"redis://{settings.redis.HOST}:{settings.redis.PORT}/0",
    result_backend=f"redis://{settings.redis.HOST}:{settings.redis.PORT}/0",
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Регистрация всех модулей с задачами
    include=[
        "app.worker.tasks",           # Парсинг и генерация (Спринт 2-3)
        "app.worker.grading_tasks",   # Оценка HGC (Спринт 4)
        "app.worker.maintenance_tasks" # [NEW] Архивация и очистка (Спринт 5)
    ],
)

# Настройки для стабильности в EdTech системе
celery.conf.task_acks_late = True
celery.conf.worker_prefetch_multiplier = 1

# Опционально: Настройка периодических задач (Celery Beat)
# В реальном продакшене здесь настраивается запуск anonymize_old_sessions_task раз в неделю
celery.conf.beat_schedule = {
    "anonymize-every-sunday": {
        "task": "anonymize_old_sessions_task",
        "schedule": 604800.0, # Раз в неделю
    },
}