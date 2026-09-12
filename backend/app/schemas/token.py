from typing import Optional
from app.schemas.base import APIModel


class Token(APIModel):
    """Схема, возвращаемая клиенту при успешном логине."""
    access_token: str
    token_type: str = "bearer"


class TokenPayload(APIModel):
    """Структура данных внутри декодированного JWT токена."""
    sub: Optional[str] = None
    exp: Optional[int] = None