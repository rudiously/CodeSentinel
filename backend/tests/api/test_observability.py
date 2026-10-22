from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.settings import Settings


def test_metrics_include_unauthorized_errors() -> None:
    with TestClient(create_app(Settings())) as client:
        assert client.get("/repos").status_code == 401
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "codesentinel_api_errors_total 1.0" in response.text
        assert 'status="401"' in response.text
