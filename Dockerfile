# Production Dockerfile for Content Moderation API
# Lazy-download variant: models are loaded at runtime into /app/.cache/huggingface (mount as volume)

# ============================================
# Stage 1: Builder - Install dependencies
# ============================================
FROM python:3.11-slim as builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive \
    APP_HOME=/app \
    HF_HOME=/app/.cache/huggingface \
    TRANSFORMERS_CACHE=/app/.cache/huggingface \
    HF_HUB_CACHE=/app/.cache/huggingface \
    TORCH_HOME=/app/.cache/torch

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libpq-dev \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install
COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# NOTE: Removed build-time model download. We will lazy-download models at runtime into a mounted volume.

# ============================================
# Stage 2: Production - Runtime image
# ============================================
FROM python:3.11-slim as production

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    APP_HOME=/app \
    HF_HOME=/app/.cache/huggingface \
    TRANSFORMERS_CACHE=/app/.cache/huggingface \
    HF_HUB_CACHE=/app/.cache/huggingface \
    TORCH_HOME=/app/.cache/torch \
    PATH="/opt/venv/bin:$PATH" \
    HOME=/app

# Runtime dependencies (include common libs for numpy/torch)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    ca-certificates \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create app directory and cache directory
RUN mkdir -p ${APP_HOME} /app/.cache/huggingface /app/logs

# Create non-root user with /app as home directory
RUN groupadd -r appuser && \
    useradd -r -g appuser -u 1000 -d /app -m -s /sbin/nologin appuser

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# IMPORTANT: do NOT copy model cache from builder (lazy-download approach)
# COPY --from=builder /app/.cache/huggingface /app/.cache/huggingface  <-- removed

# Set permissions for venv, app and caches BEFORE switching user
RUN chown -R appuser:appuser ${APP_HOME} /app/.cache /app/logs /opt/venv

# Set working directory
WORKDIR ${APP_HOME}

# Copy application files (owned by appuser)
COPY --chown=appuser:appuser main.py .
COPY --chown=appuser:appuser ml_classifier.py .
COPY --chown=appuser:appuser social_media.py .

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
