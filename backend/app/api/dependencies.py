from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.db.session import get_db  # реэкспортируем, не определяем заново
from app.models.user import User, UserRole
from app.schemas.token import TokenPayload

# Указываем FastAPI, где брать токен. 
# tokenUrl должен совпадать с эндпоинтом логина, который мы напишем позже.
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.project.API_V1_STR}/auth/login"
)


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str, Depends(reusable_oauth2)]
) -> User:
    """
    Проверяет JWT токен, декодирует его и возвращает текущего пользователя из БД.
    """
    try:
        payload = jwt.decode(
            token, settings.app.SECRET_KEY, algorithms=[settings.app.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    
    # Ищем пользователя по ID из токена
    result = await db.execute(select(User).where(User.id == token_data.sub))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    return user


class RoleChecker:
    """
    Универсальный класс для проверки ролей.
    Использование: Depends(RoleChecker([UserRole.TEACHER, UserRole.ADMIN]))
    """
    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in self.allowed_roles and not user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The user doesn't have enough privileges"
            )
        return user