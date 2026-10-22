FROM python:3.11.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY model_service/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir torch==2.7.1 --index-url https://download.pytorch.org/whl/cpu && pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --create-home appuser
COPY shared /app/shared
COPY model_service /app/model_service
COPY ml /app/ml
USER 10001
EXPOSE 8001
CMD ["uvicorn", "model_service.app.main:app", "--host", "0.0.0.0", "--port", "8001", "--no-access-log"]
