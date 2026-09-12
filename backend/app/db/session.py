# app/db/session.py
import os
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

_engine: Optional[AsyncEngine] = None
_session_maker: Optional[async_sessionmaker] = None

def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        # В проде создаем здесь, в тестах он будет уже подменен через conftest
        _engine = create_async_engine(
            str(settings.postgres.DATABASE_URL),
            pool_pre_ping=True,
            future=True,
        )
    return _engine

def get_session_maker() -> async_sessionmaker:
    global _session_maker
    if _session_maker is None:
        _session_maker = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _session_maker

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    # Используем фабрику напрямую
    factory = get_session_maker()
    async with factory() as session:
        yield session