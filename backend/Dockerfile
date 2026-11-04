FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY alembic.ini ./alembic.ini
COPY migrations ./migrations

EXPOSE 5000
CMD ["uvicorn", "backend.auth_service.app:app", "--host", "0.0.0.0", "--port", "5000"]
