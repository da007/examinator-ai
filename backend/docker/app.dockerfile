# syntax=docker/dockerfile:1

# ─────────────────────────────────────────
# Stage 1: builder — компилируем зависимости
# ─────────────────────────────────────────
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    HF_HOME=/app/.cache/huggingface \
    TRANSFORMERS_CACHE=/app/.cache/huggingface \
    PIP_NO_CACHE_DIR=0 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ ./requirements/

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install \
    --default-timeout=1000 \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    --prefix=/install \
    -r requirements/ml.txt


# ─────────────────────────────────────────
# Stage 2: final — минимальный runtime образ
# ─────────────────────────────────────────
FROM python:3.11-slim AS final

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    HF_HOME=/app/.cache/huggingface \
    TRANSFORMERS_CACHE=/app/.cache/huggingface

WORKDIR /app

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY . .

RUN dos2unix scripts/prestart.sh && chmod +x scripts/prestart.sh

RUN mkdir -p /app/.cache/huggingface && \
    useradd -m appuser || echo "User already exists" && \
    chown -R appuser:appuser /app && \
    chmod -R 775 /app/.cache

USER appuser

EXPOSE 8000

CMD ["/bin/bash", "-c", "/app/scripts/prestart.sh && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers"]


# ─────────────────────────────────────────
# Stage 3: test — образ для прогона тестов
# Наследуется от builder, не от final:
# - не тащит prestart.sh, dos2unix, appuser
# - не тащит ML (torch) — ставим только test.txt
# - работает под root (нормально для CI)
# ─────────────────────────────────────────
FROM python:3.11-slim AS test

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    ENV=TESTING \
    CELERY_TASK_ALWAYS_EAGER=True

WORKDIR /app

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ ./requirements/

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install \
    --default-timeout=1000 \
    -r requirements/test.txt

COPY app/ ./app/
COPY tests/ ./tests/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY pytest.ini .

CMD ["pytest", "tests/", "-v", "--disable-warnings"]