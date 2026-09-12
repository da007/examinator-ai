from datetime import datetime, timedelta, timezone
from typing import Any, Union

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

# Настройка контекста хеширования. 
# bcrypt автоматически обрабатывает соль, что защищает от радужных таблиц.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(
    subject: Union[str, Any], expires_delta: timedelta = None
) -> str:
    """
    Создает подписанный JWT токен.
    :param subject: Обычно это ID пользователя (uuid), который будет храниться в поле 'sub'.
    :param expires_delta: Время жизни токена.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.app.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    # Payload токена. Не кладите сюда чувствительные данные (пароли), 
    # так как содержимое JWT можно прочитать без ключа.
    to_encode = {"exp": expire, "sub": str(subject)}
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.app.SECRET_KEY, 
        algorithm=settings.app.ALGORITHM
    )
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяет соответствие чистого пароля его хешу.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Генерирует хеш из пароля.
    """
    return pwd_context.hash(password)