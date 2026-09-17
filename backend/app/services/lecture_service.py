import uuid
from typing import List, Optional
import aioboto3
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.chunk import Chunk
from sqlalchemy import delete

from app.core.config import settings
from app.models.lecture import Lecture, LectureStatus
from app.schemas.lecture import LectureCreate, LectureUpdate


class LectureService:
    def __init__(self):
        pass

    async def _get_s3_client(self):
        session = aioboto3.Session()  
        return session.client(
            "s3",
            endpoint_url=settings.s3.ENDPOINT,
            aws_access_key_id=settings.s3.ACCESS_KEY,
            aws_secret_access_key=settings.s3.SECRET_KEY,
            use_ssl=settings.s3.USE_SSL,
        )

    async def get_multi_by_org(
        self, db: AsyncSession, *, org_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> List[Lecture]:
        """Получение списка лекций с фильтрацией по организации (Multi-tenancy)."""
        query = (
            select(Lecture)
            .where(Lecture.org_id == org_id)
            .offset(skip)
            .limit(limit)
            .order_by(Lecture.created_at.desc())
        )
        result = await db.execute(query)
        return result.scalars().all()

    async def update(
        self, db: AsyncSession, *, db_obj: Lecture, obj_in: LectureUpdate
    ) -> Lecture:
        """
        Обновление данных лекции (название, статус, дедлайны).
        """
        # Превращаем схему в словарь, исключая неустановленные поля
        update_data = obj_in.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def create_with_file(
        self, 
        db: AsyncSession, 
        *, 
        obj_in: LectureCreate, 
        teacher_id: uuid.UUID,
        file_content: bytes,
        extension: str
    ) -> Lecture:
        """
        Создает запись в БД и загружает файл в S3.
        """
        # 1. Создаем объект в БД со статусом UPLOADED
        db_obj = Lecture(
            title=obj_in.title,
            org_id=obj_in.org_id,
            subject_id=obj_in.subject_id,
            teacher_id=teacher_id,
            status=LectureStatus.UPLOADED,
        
            open_from=obj_in.open_from,
            deadline_at=obj_in.deadline_at,
            exam_duration_minutes=obj_in.exam_duration_minutes,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)

        # 2. Формируем путь к файлу в S3: org_id/lecture_id.ext
        file_key = f"{db_obj.org_id}/{db_obj.id}.{extension}"

        # 3. Загружаем файл в S3
        async with await self._get_s3_client() as s3:
            await s3.put_object(
                Bucket=settings.s3.BUCKET_NAME,
                Key=file_key,
                Body=file_content
            )
        
        return db_obj

    async def update_status(
        self, db: AsyncSession, *, db_obj: Lecture, status: LectureStatus
    ) -> Lecture:
        """Обновление статуса лекции (используется воркерами)."""
        db_obj.status = status
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def delete(self, db: AsyncSession, *, db_obj: Lecture) -> bool:
        """
        Удаляет запись лекции из БД. 
        Зависимые данные (чанки, вопросы, сессии) удалятся каскадно на уровне СУБД.
        """
        await db.delete(db_obj)
        await db.commit()
        return True
        
    async def prepare_for_regeneration(self, db: AsyncSession, *, db_obj: Lecture) -> str:
        """
        Очищает старые результаты генерации и возвращает путь к файлу в S3.
        """
        # 1. Удаляем все чанки (вопросы удалятся каскадно на уровне БД)
        await db.execute(delete(Chunk).where(Chunk.lecture_id == db_obj.id))
        
        # 2. Сбрасываем статус
        db_obj.status = LectureStatus.PROCESSING
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)

        # 3. Определяем ключ файла в S3 (логика как в download)
        # Находим расширение файла, проверяя существование в S3
        file_key_base = f"{db_obj.org_id}/{db_obj.id}"
        found_key = f"{file_key_base}.docx" # default
        
        async with await self._get_s3_client() as s3:
            for ext in ['docx', 'txt']:
                try:
                    test_key = f"{file_key_base}.{ext}"
                    await s3.head_object(Bucket=settings.s3.BUCKET_NAME, Key=test_key)
                    found_key = test_key
                    break
                except:
                    continue
        
        return found_key


lecture_service = LectureService()