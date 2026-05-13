# ============================================================
# OptiWallet Backend — Multi-stage Dockerfile
# ============================================================
# Python 3.12 slim image, optimize edilmiş build
# ============================================================

# ----- Stage 1: Builder -----
FROM python:3.12-slim AS builder

# Build-time environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VIRTUALENVS_CREATE=false

# System dependencies (build için gerekli)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependency dosyalarını kopyala (cache optimization)
COPY pyproject.toml ./

# Python paketlerini kur
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -e .

# ----- Stage 2: Runtime -----
FROM python:3.12-slim AS runtime

# Runtime environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/usr/local/bin:$PATH"

# Runtime system dependencies (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Non-root kullanıcı oluştur (security best practice)
RUN groupadd -r optiwallet && \
    useradd -r -g optiwallet -d /app -s /sbin/nologin optiwallet

WORKDIR /app

# Builder stage'den paketleri kopyala
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Uygulama kodunu kopyala
COPY --chown=optiwallet:optiwallet . .

# Non-root kullanıcıya geç
USER optiwallet

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Default command (docker-compose.yml override edebilir)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]