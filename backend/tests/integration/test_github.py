import base64
import json
from pathlib import Path

import httpx
import pytest

from action.gate import exit_code, scan_and_comment
from backend.app.services.github_client import GitHubClient
from shared.http import ServiceError
from shared.schemas import ScanReport


def test_fake_github_collect_comment_and_check() -> None:
    seen: list[str] = []

    def fake(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        assert request.url.host == "api.github.com"
        if "/files" in request.url.path:
            return httpx.Response(
                200, json=[{"status": "modified", "filename": "a.py", "sha": "a" * 40}]
            )
        if "/git/blobs/" in request.url.path:
            content = base64.b64encode(b"def f():\n    return 1\n").decode()
            return httpx.Response(
                200, json={"encoding": "base64", "size": 22, "content": content}
            )
        return httpx.Response(201, json={"id": 1})

    github = GitHubClient("fake-test-token", httpx.MockTransport(fake))
    assert github.collect("demo/repo", 1).files[0].code.startswith("def f")
    report = ScanReport.model_validate_json(
        Path("fixtures/scan_report.json").read_text()
    )
    github.post_report("demo/repo", 1, "a" * 40, report)
    assert any("/comments" in url for url in seen) and any(
        "/check-runs" in url for url in seen
    )
    with pytest.raises(ServiceError):
        github.request("GET", "https://evil.test/steal")
    github.close()


def test_action_fake_http_block_fails_and_comment_labelled() -> None:
    data = json.loads(Path("fixtures/scan_report.json").read_text())
    data.update(decision="BLOCK", risk_score=0.9)
    calls: list[str] = []

    def fake(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.host)
        if request.url.host == "scanner.test":
            assert request.headers["Authorization"] == "Bearer api-test-token"
            return httpx.Response(200, json=data)
        assert request.headers["Authorization"] == "Bearer github-test-token"
        assert "STUB" in json.loads(request.content)["body"]
        assert "return a + b" not in request.content.decode()
        return httpx.Response(201, json={"id": 1})

    with httpx.Client(transport=httpx.MockTransport(fake)) as client:
        report = scan_and_comment(
            client,
            "https://scanner.test",
            "demo/repo",
            1,
            {"files": []},
            "github-test-token",
            "api-test-token",
        )
    assert exit_code(report) == 1 and calls == ["scanner.test", "api.github.com"]
    assert (
        exit_code(report.model_copy(update={"decision": "ERROR", "risk_score": None}))
        == 2
    )


def test_app_installation_token_exchange_uses_fixed_origin() -> None:
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    paths: list[str] = []

    def fake(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.github.com"
        paths.append(request.url.path)
        if request.url.path == "/app/installations/123/access_tokens":
            assert request.headers["Authorization"].startswith("Bearer ey")
            return httpx.Response(201, json={"token": "fake-installation-token"})
        assert request.headers["Authorization"] == "Bearer fake-installation-token"
        return httpx.Response(200, json=[])

    github = GitHubClient(
        "", httpx.MockTransport(fake), app_id="99", installation_id=123, private_key=pem
    )
    github.request("GET", "/repos/demo/repo/pulls/1/files")
    assert paths == [
        "/app/installations/123/access_tokens",
        "/repos/demo/repo/pulls/1/files",
    ]
    github.close()
