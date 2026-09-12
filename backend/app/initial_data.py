import asyncio
import logging
import uuid
import aioboto3
from botocore.exceptions import ClientError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.session import get_session_maker
from app.models.user import User, UserRole
from app.models.subject import Subject

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_first_superuser(db: AsyncSession) -> None:
    """Создаёт первого суперпользователя из .env при первом запуске."""
    from sqlalchemy import select

    result = await db.execute(
        select(User).where(User.email == settings.init.SUPERUSER_EMAIL)
    )
    user = result.scalar_one_or_none()

    if not user:
        new_user = User(
            email=settings.init.SUPERUSER_EMAIL,
            hashed_password=get_password_hash(settings.init.SUPERUSER_PASSWORD),
            full_name="System Administrator",
            role=UserRole.ADMIN,
            org_id=uuid.UUID(str(settings.init.SUPERUSER_ORG_ID)),
            is_superuser=True,
            is_active=True,
        )
        db.add(new_user)
        await db.commit()
        
        await db.refresh(new_user)
        logger.info(f"Superuser {settings.init.SUPERUSER_EMAIL} created.")
        
        return new_user
    else:
        logger.info("Superuser already exists.")
        return user

async def create_default_subject(db: AsyncSession, admin: User) -> None:
    """Создает базовую дисциплину для тестов."""
    from sqlalchemy import select
    res = await db.execute(select(Subject).where(Subject.name == "Основы ИИ"))
    if not res.scalar_one_or_none():
        sub = Subject(
            name="Основы ИИ",
            description="Тестовая дисциплина",
            org_id=admin.org_id,
            teacher_id=admin.id
        )
        db.add(sub)
        await db.commit()
        logger.info("Default subject 'Основы ИИ' created.")

async def init_s3() -> None:
    """Создаёт начальный бакет в MinIO если его нет."""
    session = aioboto3.Session()
    async with session.client(
        "s3",
        endpoint_url=settings.s3.ENDPOINT,
        aws_access_key_id=settings.s3.ACCESS_KEY,
        aws_secret_access_key=settings.s3.SECRET_KEY,
        use_ssl=settings.s3.USE_SSL,
    ) as s3:
        try:
            await s3.head_bucket(Bucket=settings.s3.BUCKET_NAME)
            logger.info(f"S3 Bucket '{settings.s3.BUCKET_NAME}' already exists.")
        except ClientError as e:
            # ИСПРАВЛЕНО: было голый except: — маскировал любые ошибки включая сетевые.
            # Теперь ловим только ClientError (бакет не найден = 404/NoSuchBucket).
            error_code = e.response["Error"]["Code"]
            if error_code in ("404", "NoSuchBucket"):
                await s3.create_bucket(Bucket=settings.s3.BUCKET_NAME)
                logger.info(f"S3 Bucket '{settings.s3.BUCKET_NAME}' created.")
            else:
                raise


async def main() -> None:
    logger.info("Creating initial data...")
    async with get_session_maker()() as db:
        admin = await create_first_superuser(db)
        await create_default_subject(db, admin)

    logger.info("Initializing S3 storage...")
    await init_s3()
    logger.info("Initial data created successfully.")


if __name__ == "__main__":
    asyncio.run(main())