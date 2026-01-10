# syntax=docker/dockerfile:1
# Multi-Agent Personal Assistant API container

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r ./requirements.txt

# Copy project source
COPY . .

# Expose API port (override by setting PORT/APP_PORT/DEFAULT_PORT env variables)
EXPOSE 8080

# Default command: production server via Waitress (WSGI)
# For async-first serving, you can alternatively use Uvicorn:
#   CMD ["uvicorn", "config.asgi:application", "--host", "0.0.0.0", "--port", "8080"]
CMD ["python", "run_server.py"]
