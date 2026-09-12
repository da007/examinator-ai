from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
 
from app.api.v1.api import api_router
from app.core.config import settings
 
 
def get_application() -> FastAPI:
    _app = FastAPI(
        title=settings.project.NAME,
        openapi_url=f"{settings.project.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )
 
    # ИСПРАВЛЕНО: было settings.BACKEND_CORS_ORIGINS — такого поля нет в корневом Settings.
    # В config.py нет класса для CORS, BACKEND_CORS_ORIGINS читается напрямую из env.
    # Правильное решение: добавить в Settings или читать через os.getenv.
    # Добавляем через AppSettings или отдельно — здесь используем прямой импорт из os.
    import os, json
    cors_origins_raw = os.getenv("BACKEND_CORS_ORIGINS", '["http://localhost:3000","http://localhost:8000"]')
    try:
        cors_origins = json.loads(cors_origins_raw)
    except (json.JSONDecodeError, TypeError):
        cors_origins = [cors_origins_raw]
 
    if cors_origins:
        '''_app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in cors_origins],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )'''
        _app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Разрешить любой адрес (включая localhost:5173)
            allow_credentials=True,
            allow_methods=["*"],  # Разрешить все методы (GET, POST, etc.)
            allow_headers=["*"],  # Разрешить все заголовки
        )
 
    _app.include_router(api_router, prefix=settings.project.API_V1_STR)
 
    @_app.get("/health", tags=["health"])
    async def health_check():
        return {"status": "ok", "project": settings.project.NAME}
 
    return _app
 
 
app = get_application()
 
