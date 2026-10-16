# Backend image for Fly.io — FastAPI + OR-Tools.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps (psycopg + general build hygiene). slim images need these.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

EXPOSE 8080

# Fly sets PORT; default to 8080. One worker keeps OR-Tools memory predictable.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
