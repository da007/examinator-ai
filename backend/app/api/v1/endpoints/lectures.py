import uuid
from typing import Any, List, Optional
from datetime import datetime as dt_parse
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import dependencies
from app.models.user import User, UserRole
from app.models.lecture import Lecture, LectureStatus
from app.schemas.lecture import LectureRead, LectureCreate, LectureUpdate
from app.models.subject import Subject

from app.services.lecture_service import lecture_service
from app.services.question_service import question_service
from app.worker.tasks import process_lecture_task

router = APIRouter()

@router.post("/upload", response_model=LectureRead, status_code=status.HTTP_202_ACCEPTED)
async def upload_lecture(
    *,
    db: AsyncSession = Depends(dependencies.get_db),
    current_user: User = Depends(dependencies.RoleChecker([UserRole.TEACHER, UserRole.ADMIN])),
    title: str = Form(...),
    subject_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    open_from: Optional[str] = Form(None),           # ISO-строка даты открытия доступа или null
    deadline_at: Optional[str] = Form(None),          # ISO-строка дедлайна или null
    exam_duration_minutes: Optional[int] = Form(None) # лимит времени на прохождение экзамена, в минутах
) -> Any:
    """
    Загрузка новой лекции в рамках конкретной дисциплины (Subject).
    
    Логика:
    1. Проверка расширения файла.
    2. Проверка существования дисциплины и принадлежности её к той же организации (org_id).
    3. Сохранение метаданных в БД и файла в S3.
    4. Запуск фоновой задачи парсинга и генерации вопросов.
    """
    
    # 1. Валидация формата файла — разрешены только текстовые/докс-документы
    extension = file.filename.split('.')[-1].lower()
    if extension not in ["docx", "txt"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Поддерживаются только .docx и .txt файлы"
        )

    # 2. Проверка прав доступа к дисциплине (Multi-tenancy check)
    # Мы должны убедиться, что преподаватель не загружает лекцию в чужой курс
    subject_query = select(Subject).where(Subject.id == subject_id)
    subject_result = await db.execute(subject_query)
    subject = subject_result.scalar_one_or_none()
    
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Указанная дисциплина не найдена"
        )
    
    # Проверка изоляции данных
    if subject.org_id != current_user.org_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Вы не можете добавлять лекции в дисциплины другой организации"
        )

    # 3. Чтение контента и создание записи
    content = await file.read()

    # Парсим опциональные ISO-строки дат в datetime; при некорректном формате — тихо возвращаем None
    def _parse_dt(s: Optional[str]):
        if not s:
            return None
        try:
            return dt_parse.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None

    lecture_in = LectureCreate(
        title=title,
        org_id=current_user.org_id,
        subject_id=subject_id,
        open_from=_parse_dt(open_from),
        deadline_at=_parse_dt(deadline_at),
        exam_duration_minutes=exam_duration_minutes,
    )

    # Вызов сервиса (создает запись в БД и кладет файл в S3)
    db_obj = await lecture_service.create_with_file(
        db, 
        obj_in=lecture_in, 
        teacher_id=current_user.id,
        file_content=content,
        extension=extension
    )

    # 4. Постановка задачи в Celery для извлечения текста и генерации вопросов
    # Ключ файла строится по той же схеме {org_id}/{lecture_id}.{ext}, что и при сохранении в S3
    file_key = f"{db_obj.org_id}/{db_obj.id}.{extension}"
    process_lecture_task.delay(str(db_obj.id), file_key)

    return db_obj

@router.get("/", response_model=List[LectureRead])
async def read_lectures(
    subject_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(dependencies.get_db),
    current_user: User = Depends(dependencies.get_current_user),
) -> Any:
    # Список лекций всегда ограничен организацией пользователя; фильтр по subject_id опциональный
    query = select(Lecture).where(Lecture.org_id == current_user.org_id)
    if subject_id:
        query = query.where(Lecture.subject_id == subject_id)

    # Студент видит только готовые и опубликованные лекции
    if current_user.role == UserRole.STUDENT:
        query = query.where(
            Lecture.status == LectureStatus.PUBLISHED
        )

    query = query.order_by(Lecture.created_at.desc())

    # Выполняем запрос и достаём объекты из результата
    result = await db.execute(query)
    lectures = result.scalars().all()
        
    return lectures 

@router.get("/{lecture_id}", response_model=LectureRead)
async def read_lecture(
    lecture_id: uuid.UUID,
    db: AsyncSession = Depends(dependencies.get_db),
    current_user: User = Depends(dependencies.get_current_user),
) -> Any:
    """
    Получение детальной информации о лекции.
    """
    query = select(Lecture).where(Lecture.id == lecture_id)
    result = await db.execute(query)
    lecture = result.scalar_one_or_none()
    
    if not lecture:
        raise HTTPException(status_code=404, detail="Лекция не найдена")
    
    # Проверка прав доступа (Multi-tenancy)
    if lecture.org_id != current_user.org_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Доступ к этой лекции запрещен")
        
    return lecture

@router.post("/{lecture_id}/publish", response_model=LectureRead)
async def publish_lecture(
    lecture_id: uuid.UUID,
    db: AsyncSession = Depends(dependencies.get_db),
    current_user: User = Depends(dependencies.RoleChecker([UserRole.TEACHER, UserRole.ADMIN])),
) -> Any:
    """Публикация лекции."""
    # Вся проверка прав/статуса — внутри сервиса; он же меняет статус лекции на PUBLISHED
    lecture = await question_service.publish_lecture(
        db, lecture_id=lecture_id, org_id=current_user.org_id
    )
    if not lecture:
        raise HTTPException(status_code=404, detail="Лекция не найдена")
    return lecture

@router.delete("/{lecture_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lecture(
    lecture_id: uuid.UUID,
    db: AsyncSession = Depends(dependencies.get_db),
    current_user: User = Depends(dependencies.RoleChecker([UserRole.TEACHER, UserRole.ADMIN])),
):
    """
    Удаление лекции и всех связанных данных.
    Доступно только владельцу (той же организации) или суперпользователю.
    """
    query = select(Lecture).where(Lecture.id == lecture_id)
    result = await db.execute(query)
    lecture = result.scalar_one_or_none()
    
    if not lecture:
        raise HTTPException(status_code=404, detail="Лекция не найдена")
    
    # Multi-tenancy check
    if lecture.org_id != current_user.org_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Доступ к удалению этой лекции запрещен")
        
    await lecture_service.delete(db, db_obj=lecture)
    
    # Для 204 статуса возвращаем пустой Response
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.patch("/{lecture_id}", response_model=LectureRead)
async def update_lecture(
    lecture_id: uuid.UUID,
    obj_in: LectureUpdate,
    db: AsyncSession = Depends(dependencies.get_db),
    current_user: User = Depends(dependencies.RoleChecker([UserRole.TEACHER, UserRole.ADMIN])),
) -> Any:
    """
    Обновление метаданных лекции (например, изменение названия или дедлайнов).
    Доступно только преподавателю той же организации или суперпользователю.
    """
    # 1. Ищем лекцию
    query = select(Lecture).where(Lecture.id == lecture_id)
    result = await db.execute(query)
    lecture = result.scalar_one_or_none()
    
    if not lecture:
        raise HTTPException(status_code=404, detail="Лекция не найдена")
    
    # 2. Проверка прав (Multi-tenancy)
    if lecture.org_id != current_user.org_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="У вас нет прав на редактирование этой лекции")

    # 3. Обновление через сервис (частичное обновление полей из obj_in)
    return await lecture_service.update(db, db_obj=lecture, obj_in=obj_in)

@router.get("/{lecture_id}/download")
async def download_lecture_file(
    lecture_id: uuid.UUID,
    db: AsyncSession = Depends(dependencies.get_db),
    current_user: User = Depends(dependencies.RoleChecker([UserRole.TEACHER, UserRole.ADMIN])),
):
    """
    Скачивание оригинального файла лекции из S3.
    """
    # 1. Ищем лекцию и проверяем доступ
    query = select(Lecture).where(Lecture.id == lecture_id)
    result = await db.execute(query)
    lecture = result.scalar_one_or_none()
    
    if not lecture or (lecture.org_id != current_user.org_id and not current_user.is_superuser):
        raise HTTPException(status_code=404, detail="Лекция не найдена")

    # 2. Получаем объект из S3.
    # Расширение исходного файла в БД отдельно не хранится, поэтому перебираем
    # поддерживаемые варианты (docx/txt) и ищем, какой ключ реально существует в бакете.
    import aioboto3
    from app.core.config import settings
    
    file_key_base = f"{lecture.org_id}/{lecture.id}"
    
    session = aioboto3.Session()
    async with session.client("s3", endpoint_url=settings.s3.ENDPOINT, 
                              aws_access_key_id=settings.s3.ACCESS_KEY,
                              aws_secret_access_key=settings.s3.SECRET_KEY) as s3:
        # Пытаемся найти файл с любым из поддерживаемых расширений
        found_key = None
        for ext in ['docx', 'txt']:
            try:
                test_key = f"{file_key_base}.{ext}"
                await s3.head_object(Bucket=settings.s3.BUCKET_NAME, Key=test_key)
                found_key = test_key
                break
            except:
                continue
        
        if not found_key:
            raise HTTPException(status_code=404, detail="Файл в хранилище не найден")

        response = await s3.get_object(Bucket=settings.s3.BUCKET_NAME, Key=found_key)
        
        return StreamingResponse(
            response['Body'],
            media_type=response['ContentType'],
            headers={"Content-Disposition": f"attachment; filename={lecture.title}.{found_key.split('.')[-1]}"}
        )

@router.post("/{lecture_id}/regenerate", response_model=LectureRead)
async def regenerate_lecture(
    lecture_id: uuid.UUID,
    db: AsyncSession = Depends(dependencies.get_db),
    current_user: User = Depends(dependencies.RoleChecker([UserRole.TEACHER, UserRole.ADMIN])),
) -> Any:
    """
    Полная перегенерация вопросов лекции.
    Удаляет существующие чанки и вопросы, затем перезапускает воркер.
    """
    # Получаем лекцию с проверкой прав
    query = select(Lecture).where(Lecture.id == lecture_id)
    result = await db.execute(query)
    lecture = result.scalar_one_or_none()

    if not lecture or (lecture.org_id != current_user.org_id and not current_user.is_superuser):
        raise HTTPException(status_code=404, detail="Лекция не найдена")

    # Вызываем сервис для очистки данных (старые чанки/вопросы удаляются) и получения ключа файла
    file_key = await lecture_service.prepare_for_regeneration(db, db_obj=lecture)

    # Запускаем задачу заново — весь пайплайн парсинга/генерации вопросов пройдёт с нуля
    process_lecture_task.delay(str(lecture.id), file_key)

    return lecture