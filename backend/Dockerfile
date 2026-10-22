FROM python:3.11.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends cppcheck=2.10-2 && rm -rf /var/lib/apt/lists/* && useradd --uid 10001 --create-home appuser
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY shared /app/shared
COPY backend /app/backend
RUN chown -R 10001:10001 /app
USER 10001
EXPOSE 8000
CMD ["sh", "-c", "alembic -c backend/alembic.ini upgrade head && exec uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --no-access-log"]
