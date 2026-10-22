import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.settings import Settings


def signed(
    body: bytes, event: str = "pull_request", delivery: str = "delivery-1"
) -> dict[str, str]:
    return {
        "X-Hub-Signature-256": "sha256="
        + hmac.new(b"test-secret", body, hashlib.sha256).hexdigest(),
        "X-GitHub-Event": event,
        "X-GitHub-Delivery": delivery,
    }


def test_signature_checked_before_json_parsing() -> None:
    with TestClient(
        create_app(Settings(github_webhook_secret="test-secret"))
    ) as client:
        response = client.post(
            "/webhook/github",
            content=b"not json",
            headers={"X-Hub-Signature-256": "sha256=bad"},
        )
        assert (
            response.status_code == 401
            and response.json()["error"]["code"] == "INVALID_SIGNATURE"
        )
        assert (
            client.post(
                "/webhook/github", content=b"not json", headers=signed(b"not json")
            ).status_code
            == 422
        )


def test_unsupported_replay_is_ignored() -> None:
    with TestClient(
        create_app(Settings(github_webhook_secret="test-secret"))
    ) as client:
        for _ in range(2):
            assert client.post(
                "/webhook/github", content=b"{}", headers=signed(b"{}", "push")
            ).json() == {"status": "ignored"}


def test_valid_delivery_only_processed_once_and_failed_delivery_retryable() -> None:
    app = create_app(Settings(github_webhook_secret="test-secret"))
    payload = json.dumps(
        {
            "action": "opened",
            "number": 1,
            "repository": {"full_name": "demo/repo"},
            "pull_request": {"head": {"sha": "a" * 40}},
        }
    ).encode()
    calls: list[str] = []

    def handler(repo: str, number: int, sha: str) -> dict[str, str]:
        calls.append(repo)
        return {"status": "processed"}

    with TestClient(app) as client:
        assert (
            client.post(
                "/webhook/github", content=payload, headers=signed(payload)
            ).status_code
            == 503
        )
        app.state.github_handler = handler
        assert client.post(
            "/webhook/github", content=payload, headers=signed(payload)
        ).json() == {"status": "processed"}
        assert client.post(
            "/webhook/github", content=payload, headers=signed(payload)
        ).json() == {"status": "duplicate"}
    assert calls == ["demo/repo"]
