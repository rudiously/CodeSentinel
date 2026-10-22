import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.main import create_app as original_create_app
from backend.app.db.models import Base


from backend.app.services.model_client import ModelClient
from backend.app.settings import Settings
from model_service.stub_model import predict


def fake_model(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/model/info":
        return httpx.Response(
            200,
            json={
                "model_mode": "stub",
                "artifact_kind": "STUB",
                "model_version": "stub-v1",
            },
        )
    return httpx.Response(200, json=predict("safe"))


def create_app(
    settings: Settings | None = None, model_client: ModelClient | None = None
) -> FastAPI:
    settings = settings or Settings()
    settings = settings.model_copy(
        update={"database_url": "sqlite:///:memory:", "auth_required": False}
    )
    app = original_create_app(settings, model_client)
    Base.metadata.create_all(app.state.store.engine)
    return app


def test_api_proxy_health_validation_and_limits() -> None:
    model = ModelClient("http://model", transport=httpx.MockTransport(fake_model))
    with TestClient(
        create_app(Settings(rate_limit_requests=3, max_request_bytes=100), model)
    ) as client:
        assert client.get("/health").json()["model_mode"] == "stub"
        assert (
            client.post("/predict", json={"code": "safe"}).json()["artifact_kind"]
            == "STUB"
        )
        invalid = client.post("/predict", json={"code": ""})
        assert invalid.status_code == 422
        assert invalid.json()["error"]["request_id"] == invalid.headers["X-Request-ID"]
        assert client.post("/predict", content=b"x" * 101).status_code == 413
        assert client.post("/predict", json={"code": "safe"}).status_code == 429


def test_dependency_down_is_explicit_error() -> None:
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("unavailable")

    with TestClient(
        create_app(
            model_client=ModelClient(
                "http://model", transport=httpx.MockTransport(down)
            )
        )
    ) as client:
        result = client.post("/predict", json={"code": "safe"})
        assert result.status_code == 503
        assert result.json()["error"]["code"] == "MODEL_UNAVAILABLE"


def test_invalid_model_response_rejected() -> None:
    model = ModelClient(
        "http://model",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"probability": 2})
        ),
    )
    with TestClient(create_app(model_client=model)) as client:
        result = client.post("/predict", json={"code": "safe"})
        assert result.status_code == 503
        assert result.json()["error"]["code"] == "MODEL_INVALID_RESPONSE"
