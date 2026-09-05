# Multi-stage production Dockerfile for Photo Studio Backend
FROM python:3.14-slim as base

# Python environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies (build-essential, curl, libpq-dev for postgres)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements/ /app/requirements/
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements/production.txt

# Copy application source
COPY . /app/

# Create a non-privileged user and adjust file permissions
RUN addgroup --system appgroup && adduser --system --group appuser \
    && mkdir -p /app/staticfiles /app/media \
    && chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

# Default entrypoint runs production WSGI with Gunicorn
CMD ["gunicorn", "config.asgi:application", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--workers", "4"]
