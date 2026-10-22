"""GitHub Actions workload identity for /scan only, scoped to allowed repositories."""

from threading import Lock
from time import monotonic
from typing import Any

import httpx
import jwt

from shared.http import ServiceError

ISSUER = "https://token.actions.githubusercontent.com"


class GitHubOIDC:
    def __init__(
        self,
        repositories: list[str],
        audience: str = "codesentinel",
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.repositories = set(repositories)
        self.audience = audience
        self.client = httpx.Client(
            timeout=5, follow_redirects=False, trust_env=False, transport=transport
        )
        self.keys: list[dict[str, Any]] = []
        self.expires = 0.0
        self.lock = Lock()

    def close(self) -> None:
        self.client.close()

    def verify(self, token: str) -> str:
        if not self.repositories:
            raise ServiceError(
                "OIDC_NOT_CONFIGURED", "Configure allowed GitHub repositories"
            )
        try:
            header = jwt.get_unverified_header(token)
            if header.get("alg") != "RS256" or not isinstance(header.get("kid"), str):
                raise ValueError("Unsupported identity token")
            with self.lock:
                if monotonic() >= self.expires:
                    response = self.client.get(ISSUER + "/.well-known/jwks")
                    response.raise_for_status()
                    if len(response.content) > 1000000:
                        raise ValueError("Oversized JWKS")
                    self.keys = response.json()["keys"]
                    self.expires = monotonic() + 300
                matching = [key for key in self.keys if key.get("kid") == header["kid"]]
                if len(matching) != 1:
                    raise ValueError("Unknown identity key")
                key = jwt.PyJWK.from_dict(matching[0], algorithm="RS256").key
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                issuer=ISSUER,
                audience=self.audience,
                options={
                    "require": ["exp", "iat", "nbf", "sub", "repository", "event_name"]
                },
            )
            repository = claims["repository"]
            if (
                repository not in self.repositories
                or claims["event_name"] != "pull_request"
                or claims["sub"] != f"repo:{repository}:pull_request"
            ):
                raise ValueError("Unauthorized repository or event")
            return str(repository)
        except (jwt.PyJWTError, httpx.HTTPError, ValueError, KeyError, TypeError):
            raise ServiceError(
                "INVALID_WORKLOAD_IDENTITY",
                "GitHub Actions identity is invalid or not authorized",
                401,
            ) from None
