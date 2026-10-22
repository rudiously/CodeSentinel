from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
import logging
from time import perf_counter
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from uuid import uuid4

from fastapi import FastAPI, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import Field

from backend.app.db.repositories import ScanStore
from backend.app.db.session import make_engine
from backend.app.schemas import ScanRequest
from backend.app.services.report_builder import build_report
from backend.app.services.github_client import GitHubClient
from backend.app.api.webhook import webhook_router
from backend.app.api.auth import auth_router, decode
from backend.app.core.rate_limit import RateLimiter
from backend.app.core.oidc import GitHubOIDC
from backend.app.logging import configure_logging
from backend.app.services.model_client import ModelClient
from backend.app.settings import Settings
from backend.app.metrics import Metrics
from backend.app.services.static_analysis.base import analyze
from shared.http import (
    BodyLimitMiddleware,
    ServiceError,
    error_response,
    install_errors,
)
from shared.schemas import ContractModel, Language, Prediction


class PredictRequest(ContractModel):
    code: str = Field(min_length=1, max_length=100000)
    language: Language = "c"


def create_app(
    settings: Settings | None = None, model_client: ModelClient | None = None
) -> FastAPI:
    config = settings or Settings()
    model = model_client or ModelClient(
        config.model_service_url, config.model_timeout_seconds
    )
    limiter = RateLimiter(config.rate_limit_requests, config.rate_limit_window_seconds)
    configure_logging()
    metrics = Metrics()
    engine = make_engine(config.database_url)
    store = ScanStore(engine)
    oidc = GitHubOIDC(config.github_allowed_repositories, config.github_oidc_audience)
    github = GitHubClient(
        config.github_token,
        app_id=config.github_app_id,
        installation_id=config.github_app_installation_id,
        private_key=config.github_app_private_key,
    )

    @asynccontextmanager
    async def lifespan(service: FastAPI) -> AsyncIterator[None]:
        yield
        model.close()
        engine.dispose()
        github.close()
        oidc.close()

    service = FastAPI(title="CodeSentinel API", lifespan=lifespan)
    service.state.settings, service.state.model = config, model
    service.state.store = store
    service.state.oidc = oidc
    if config.github_token or (
        config.github_app_id
        and config.github_app_installation_id
        and config.github_app_private_key
    ):

        def github_handler(repository: str, number: int, sha: str) -> dict[str, object]:
            github.assert_head(repository, number, sha)
            body = github.collect(
                repository, number, config.max_files, config.max_code_chars
            )
            report = build_report(body, config, model)
            store.save(report)
            github.assert_head(repository, number, sha)
            github.post_report(repository, number, sha, report)
            return {
                "status": "processed",
                "scan_id": str(report.scan_id),
                "decision": report.decision,
            }

        service.state.github_handler = github_handler
    install_errors(service)
    service.include_router(webhook_router(config.github_webhook_secret))
    service.include_router(auth_router(config))
    service.add_middleware(BodyLimitMiddleware, max_bytes=config.max_request_bytes)
    service.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @service.middleware("http")
    async def metadata(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = str(uuid4())
        request.state.request_id = request_id
        peer = request.client.host if request.client else "unknown"
        if request.url.path not in {"/health", "/metrics"} and not limiter.allow(peer):
            return error_response(
                "RATE_LIMITED", "Request rate limit exceeded", 429, request_id
            )
        public = request.url.path in {
            "/health",
            "/metrics",
            "/docs",
            "/docs/oauth2-redirect",
            "/openapi.json",
            "/webhook/github",
        } or request.url.path.startswith("/auth/")
        if config.auth_required and not public and request.method != "OPTIONS":
            authorization = request.headers.get("Authorization", "")
            if not authorization.startswith("Bearer "):
                return error_response(
                    "AUTH_REQUIRED", "Bearer session token required", 401, request_id
                )
            try:
                if config.github_oidc_enabled and request.url.path == "/scan":
                    from starlette.concurrency import run_in_threadpool

                    try:
                        decode(config, authorization[7:])
                    except ServiceError:
                        request.state.gate_repository = await run_in_threadpool(
                            service.state.oidc.verify, authorization[7:]
                        )
                else:
                    decode(config, authorization[7:])
            except ServiceError as exc:
                return error_response(exc.code, exc.message, exc.status, request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logging.getLogger("codesentinel").info(
            "request_complete",
            extra={"request_id": request_id, "status": response.status_code},
        )
        return response

    @service.get("/health")
    def health() -> dict[str, object]:
        return {"status": "ok", **model.info()}

    @service.get("/model/info")
    def info() -> dict[str, object]:
        return model.info()

    @service.post("/predict", response_model=Prediction)
    def predict(body: PredictRequest) -> Prediction:
        return model.predict(body.code, body.language)

    @service.post("/scan")
    @service.post("/analyze-pr")
    @service.post("/score-file")
    def scan(body: ScanRequest, request: Request) -> Response:
        gate_repository = getattr(request.state, "gate_repository", None)
        if gate_repository and gate_repository != body.repository:
            raise ServiceError(
                "REPOSITORY_MISMATCH",
                "Scan repository does not match workload identity",
                403,
            )
        with metrics.scan_seconds.time():
            report = build_report(body, config, model)
        metrics.scans.labels(report.decision).inc()
        from fastapi.responses import JSONResponse

        store.save(report)

        return JSONResponse(
            report.model_dump(mode="json"),
            status_code=503 if report.decision == "ERROR" else 200,
        )

    @service.get("/history")
    def history(
        repository: str | None = Query(
            default=None, pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$"
        ),
        decision: str | None = Query(
            default=None, pattern=r"^(PASS|WARN|BLOCK|ERROR)$"
        ),
        limit: int = Query(default=100, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> list[dict[str, object]]:
        return store.history(repository, decision, limit, offset)

    @service.get("/history/{scan_id}")
    def detail(scan_id: str) -> dict[str, object]:
        result = store.get(scan_id)
        if result is None:
            from shared.http import ServiceError

            raise ServiceError("NOT_FOUND", "Scan not found", 404)
        return result

    @service.get("/repos")
    def repos() -> list[dict[str, object]]:
        return store.repos()

    @service.post("/analyze")
    def static_analysis(body: PredictRequest) -> dict[str, object]:
        if len(body.code) > config.max_code_chars:
            raise ServiceError(
                "CODE_TOO_LARGE", "Code exceeds configured character limit", 413
            )
        findings = analyze(
            body.code,
            body.language,
            "submitted.py" if body.language == "python" else "submitted.c",
            config.static_analysis_mode,
        )
        return {
            "findings": [finding.model_dump() for finding in findings],
            "static_analyzer_mode": config.static_analysis_mode,
        }

    @service.get("/metrics")
    def prometheus() -> Response:
        return Response(
            generate_latest(metrics.registry), media_type=CONTENT_TYPE_LATEST
        )

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

    return service


app = create_app()
