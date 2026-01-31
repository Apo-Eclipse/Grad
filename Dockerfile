# syntax=docker/dockerfile:1
# Multi-Agent Personal Assistant API container

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies required for psycopg3
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r ./requirements.txt

# Copy project source
COPY . .

# Expose API port (override by setting PORT/APP_PORT/DEFAULT_PORT env variables)
EXPOSE 8080

# Production server via Uvicorn (ASGI) for full async support
# if more ram use 4 workers for multi-core utilization
# now its only one for the 512MB ram you have
CMD ["uvicorn", "config.asgi:application", "--host", "0.0.0.0", "--port", "8080"]
