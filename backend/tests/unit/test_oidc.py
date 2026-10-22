from datetime import datetime, timedelta, timezone
import json

from cryptography.hazmat.primitives.asymmetric import rsa
import httpx
import jwt
import pytest

from backend.app.core.oidc import GitHubOIDC, ISSUER
from shared.http import ServiceError


def test_actions_identity_scoped_to_repository_and_audience() -> None:
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private.public_key()))
    jwk.update(kid="test-key", alg="RS256", use="sig")
    calls: list[str] = []

    def fake(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "token.actions.githubusercontent.com"
        calls.append(request.url.path)
        return httpx.Response(200, json={"keys": [jwk]})

    verifier = GitHubOIDC(["demo/repo"], transport=httpx.MockTransport(fake))
    now = datetime.now(timezone.utc)
    claims = {
        "iss": ISSUER,
        "aud": "codesentinel",
        "sub": "repo:demo/repo:pull_request",
        "repository": "demo/repo",
        "event_name": "pull_request",
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=5),
    }
    token = jwt.encode(claims, private, algorithm="RS256", headers={"kid": "test-key"})
    assert verifier.verify(token) == "demo/repo"
    assert verifier.verify(token) == "demo/repo" and len(calls) == 1
    invalid = jwt.encode(
        {**claims, "repository": "other/repo"},
        private,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )
    with pytest.raises(ServiceError):
        verifier.verify(invalid)
    verifier.close()
