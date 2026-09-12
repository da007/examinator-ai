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
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY . .

RUN mkdir -p /app/.cache/huggingface && \
    useradd -m appuser || echo "User already exists" && \
    chown -R appuser:appuser /app && \
    chmod -R 775 /app/.cache

USER appuser

CMD ["celery", "-A", "app.core.celery_app", "worker", "-l", "info", "-c", "2"]