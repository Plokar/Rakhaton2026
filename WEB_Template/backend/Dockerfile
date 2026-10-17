# =============================================================================
# Backend – Production Dockerfile (multi-stage)
# =============================================================================

# ── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# --prefix, ne --user: balíčky v /root/.local by appuser (non-root níže) nepřečetl
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: Production ───────────────────────────────────────────────────────
FROM python:3.11-slim AS production

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /code

# Runtime závislosti
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    fonts-dejavu-core \
    netcat-traditional \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Zkopírovat nainstalované packages z builderu
COPY --from=builder /install /usr/local

# Zkopírovat zdrojový kód
COPY . .

RUN chmod +x /code/entrypoint.sh

# Non-root uživatel pro bezpečnost; staticfiles/media/logs založit předem, ať je pojmenované volumy převezmou
# s vlastníkem appuser (jinak collectstatic skončí na Permission denied)
RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser && \
    mkdir -p /code/staticfiles /code/media /code/logs && \
    chown -R appuser:appgroup /code

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/health/ || exit 1

ENTRYPOINT ["/code/entrypoint.sh"]
