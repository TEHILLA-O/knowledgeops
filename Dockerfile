# Multi-stage Dockerfile for KnowledgeOps RAG Platform
# syntax=docker/dockerfile:1

FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY app ./app
COPY config ./config
COPY migrations ./migrations
COPY alembic.ini ./

RUN pip install --upgrade pip hatchling && \
    pip wheel --no-deps --wheel-dir /wheels .

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash knowledgeops

COPY --from=builder /wheels /wheels
COPY pyproject.toml README.md ./
COPY app ./app
COPY config ./config
COPY migrations ./migrations
COPY alembic.ini ./
COPY scripts ./scripts
COPY evals ./evals

RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

USER knowledgeops

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
