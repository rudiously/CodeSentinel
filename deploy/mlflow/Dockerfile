FROM python:3.11.11-slim-bookworm
RUN pip install --no-cache-dir mlflow==2.22.0 && useradd --uid 10001 --create-home appuser && mkdir /data && chown appuser:appuser /data
USER 10001
WORKDIR /data
EXPOSE 5000
CMD ["mlflow", "server", "--host", "0.0.0.0", "--backend-store-uri", "sqlite:////data/mlflow.db", "--default-artifact-root", "/data/artifacts"]
