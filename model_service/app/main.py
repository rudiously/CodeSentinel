"""Contract C service; absent artifacts are explicitly STUB, corrupt ones fail closed."""

from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ml.predictor import Predictor

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from model_service.app.metrics import Metrics
from model_service.app.schemas import BatchInput, PredictInput
from model_service.app.settings import Settings
from model_service.stub_model import predict
from shared.http import BodyLimitMiddleware, ServiceError, install_errors
from shared.schemas import Prediction


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings()
    service = FastAPI(
        title="CodeSentinel model service — STUB until artifact installed"
    )
    metrics = Metrics()
    service.add_middleware(BodyLimitMiddleware, max_bytes=config.max_request_bytes)
    install_errors(service)
    loaded: Predictor | None = None
    load_failed = False
    if config.model_artifact_dir.exists() and any(config.model_artifact_dir.iterdir()):
        try:
            from ml.predictor import Predictor as ArtifactPredictor

            loaded = ArtifactPredictor(
                config.model_artifact_dir, explain_steps=config.explain_steps
            )
        except Exception:
            # A corrupt or unsupported artifact must not silently switch to STUB.
            load_failed = True

    def ensure_available() -> None:
        if load_failed:
            raise ServiceError(
                "ARTIFACT_NOT_LOADED",
                "Artifact failed integrity verification or could not be loaded",
            )

    def infer(code: str, language: str) -> Prediction:
        if not code or len(code) > config.max_code_chars:
            raise ServiceError(
                "INPUT_TOO_LARGE", "Code exceeds configured limits or is empty", 422
            )
        ensure_available()
        with metrics.inference.time():
            if loaded is not None:
                return loaded.predict(code, language)
            return Prediction.model_validate(predict(code, language))

    @service.middleware("http")
    async def observe(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        started = perf_counter()
        response = await call_next(request)
        route = request.scope.get("route")
        metrics.requests.labels(
            request.method,
            getattr(route, "path", "unmatched"),
            str(response.status_code),
        ).inc()
        metrics.latency.observe(perf_counter() - started)
        if response.status_code >= 400:
            metrics.errors.inc()
        return response

    @service.get("/health")
    def health() -> dict[str, str]:
        ensure_available()
        return {
            "status": "ok",
            "model_mode": "real" if loaded else "stub",
            "artifact_kind": (
                str(loaded.metadata["artifact_kind"]) if loaded else "STUB"
            ),
            "model_version": (
                str(loaded.metadata["model_version"]) if loaded else "stub-v1"
            ),
        }

    @service.get("/model/info")
    def info() -> dict[str, object]:
        return {
            **health(),
            "metrics": (
                {
                    key: loaded.metadata["metrics"][key]
                    for key in ["accuracy", "precision", "recall", "f1"]
                }
                if loaded and loaded.metadata["artifact_kind"] == "TRAINED"
                else None
            ),
            "thresholds": (
                loaded.metadata["thresholds"] if loaded else {"classification": 0.5}
            ),
            "limitations": [
                "SMOKE is synthetic pipeline verification only; STUB is heuristic, not trained ML",
                "Integrated gradients are approximate sensitivity, not causal evidence; unavailable for legacy artifacts",
                "Non-C model performance unvalidated",
            ],
        }

    @service.post("/predict", response_model=Prediction)
    def prediction(body: PredictInput) -> Prediction:
        return infer(body.code, body.language)

    @service.post("/predict_batch")
    def batch(body: BatchInput) -> dict[str, list[Prediction]]:
        if len(body.codes) > config.max_batch_size:
            raise ServiceError(
                "BATCH_TOO_LARGE", "Batch exceeds configured item limit", 422
            )
        return {"predictions": [infer(code, body.language) for code in body.codes]}

    @service.get("/metrics")
    def prometheus() -> Response:
        return Response(
            generate_latest(metrics.registry), media_type=CONTENT_TYPE_LATEST
        )

    return service


app = create_app()
