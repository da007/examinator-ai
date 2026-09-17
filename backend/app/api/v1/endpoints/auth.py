from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api import dependencies
from app.core import security
from app.core.config import settings
from app.models.user import User
from app.schemas.token import Token
from app.schemas.user import UserOut

router = APIRouter()


@router.post("/login", response_model=Token)
async def login_access_token(
    db: Annotated[AsyncSession, Depends(dependencies.get_db)],
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Any:
    """
    OAuth2 совместимый логин, получение access token.
    form_data.username здесь выступает как email.
    """
    
    # Ищем юзера по email (стандартное поле username в OAuth2 форме используем как email)
    result = await db.execute(
        select(User).where(User.email == form_data.username)
    )
    user = result.scalar_one_or_none()

    # Единая ошибка и для "нет юзера", и для "неверный пароль" — чтобы не палить,
    # существует ли аккаунт с таким email (защита от перебора)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )
    
    # Отдельная проверка на деактивированный аккаунт (уже после проверки пароля)
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Inactive user"
        )

    # Генерируем JWT с ограниченным сроком жизни из настроек
    access_token_expires = timedelta(minutes=settings.app.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }


@router.get("/me", response_model=UserOut)
async def read_user_me(
    current_user: Annotated[User, Depends(dependencies.get_current_user)],
) -> Any:
    """
    Получение информации о текущем авторизованном пользователе.
    """
    # Юзер уже извлечён и провалидирован в dependency (по токену из заголовка) — просто возвращаем его
    return current_user