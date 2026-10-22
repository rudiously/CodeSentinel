from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
import jwt
import pytest
from pydantic import ValidationError

from backend.app.main import create_app
from backend.app.settings import Settings

SECRET = "test-only-" + "x" * 40


def test_dev_login_and_protected_routes() -> None:
    settings = Settings(jwt_secret=SECRET, dev_login_enabled=True)
    with TestClient(create_app(settings)) as client:
        assert client.get("/repos").status_code == 401
        result = client.post("/auth/dev")
        assert result.status_code == 200 and result.json()["dev_only"]
        token = result.json()["access_token"]
        # A valid token reaches the DB route (DB initialization is outside this test).
        assert (
            jwt.decode(
                token, SECRET, algorithms=["HS256"], audience="codesentinel-api"
            )["sub"]
            == "dev-only-demo"
        )
        assert (
            client.get(
                "/history/missing", headers={"Authorization": "Bearer broken"}
            ).status_code
            == 401
        )


def test_expired_token_rejected_and_dev_off_by_default() -> None:
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": "x",
            "iss": "codesentinel",
            "aud": "codesentinel-api",
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),
            "jti": "test",
        },
        SECRET,
        algorithm="HS256",
    )
    with TestClient(create_app(Settings(jwt_secret=SECRET))) as client:
        assert client.post("/auth/dev").status_code == 403
        assert (
            client.get(
                "/repos", headers={"Authorization": f"Bearer {token}"}
            ).status_code
            == 401
        )
        assert client.get("/auth/github/callback?code=x&state=bad").status_code == 401


def test_production_rejects_insecure_switches() -> None:
    cases: list[dict[str, object]] = [
        {"dev_login_enabled": True},
        {"auth_required": False},
        {"jwt_secret": ""},
    ]
    for kwargs in cases:
        settings: dict[str, object] = {
            "environment": "production",
            "jwt_secret": SECRET,
            **kwargs,
        }
        with pytest.raises(ValidationError):
            Settings.model_validate(settings)


def test_oauth_exchange_and_browser_bound_state() -> None:
    from unittest.mock import patch
    from urllib.parse import parse_qs, urlparse
    import httpx

    settings = Settings(
        jwt_secret=SECRET,
        github_client_id="fake-client",
        github_client_secret="fake-secret",
        github_allowed_user_ids=["42"],
    )
    app = create_app(settings)

    def fake(request: httpx.Request) -> httpx.Response:
        if request.url.host == "github.com":
            return httpx.Response(200, json={"access_token": "fake-oauth-token"})
        assert request.url.host == "api.github.com"
        assert request.headers["Authorization"] == "Bearer fake-oauth-token"
        return httpx.Response(200, json={"id": 42, "login": "demo"})

    exchange = httpx.Client(transport=httpx.MockTransport(fake))
    with TestClient(app) as client:
        start = client.get("/auth/github", follow_redirects=False)
        assert start.status_code == 307
        state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
        with patch("backend.app.api.auth.httpx.Client", return_value=exchange):
            result = client.get(
                "/auth/github/callback",
                params={"code": "fake-code", "state": state},
                follow_redirects=False,
            )
        assert result.status_code == 307 and result.headers["location"].startswith(
            "http://localhost:3002/login#token="
        )
        token = result.headers["location"].split("#token=", 1)[1]
        assert (
            jwt.decode(
                token, SECRET, algorithms=["HS256"], audience="codesentinel-api"
            )["sub"]
            == "42"
        )
        assert result.headers["Cache-Control"] == "no-store"
