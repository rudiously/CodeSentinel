"""Single-installation JWT sessions and browser-bound GitHub OAuth state."""

import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
import httpx
import jwt

from backend.app.settings import Settings
from shared.http import ServiceError


def mint(
    config: Settings,
    subject: str,
    audience: str = "codesentinel-api",
    minutes: int | None = None,
) -> str:
    if len(config.jwt_secret) < 32:
        raise ServiceError(
            "AUTH_NOT_CONFIGURED", "Set JWT_SECRET to at least 32 random characters"
        )
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": subject,
            "iss": "codesentinel",
            "aud": audience,
            "iat": now,
            "exp": now + timedelta(minutes=minutes or config.jwt_expiry_minutes),
            "jti": secrets.token_urlsafe(24),
        },
        config.jwt_secret,
        algorithm="HS256",
    )


def decode(
    config: Settings, token: str, audience: str = "codesentinel-api"
) -> dict[str, Any]:
    if len(config.jwt_secret) < 32:
        raise ServiceError(
            "AUTH_NOT_CONFIGURED", "JWT signing secret is not configured"
        )
    try:
        decoded: dict[str, Any] = jwt.decode(
            token,
            config.jwt_secret,
            algorithms=["HS256"],
            audience=audience,
            issuer="codesentinel",
            options={"require": ["exp", "iat", "sub", "jti"]},
        )
        return decoded
    except jwt.PyJWTError:
        raise ServiceError("INVALID_TOKEN", "Session expired or invalid", 401) from None


def auth_router(config: Settings) -> APIRouter:
    router = APIRouter(prefix="/auth")

    @router.get("/config")
    def auth_config() -> dict[str, bool]:
        return {
            "dev_login_enabled": config.dev_login_enabled
            and config.environment != "production",
            "github_enabled": bool(
                config.github_client_id and config.github_client_secret
            ),
            "auth_required": config.auth_required,
        }

    @router.post("/dev")
    def dev_login() -> dict[str, object]:
        if config.environment == "production" or not config.dev_login_enabled:
            raise ServiceError(
                "DEV_LOGIN_DISABLED", "Development login is disabled", 403
            )
        return {
            "access_token": mint(config, "dev-only-demo"),
            "token_type": "bearer",
            "dev_only": True,
            "expires_in": config.jwt_expiry_minutes * 60,
        }

    @router.get("/github")
    def github_login() -> RedirectResponse:
        if not config.github_client_id or not config.github_client_secret:
            raise ServiceError(
                "OAUTH_NOT_CONFIGURED", "GitHub OAuth credentials are missing"
            )
        state = mint(config, secrets.token_urlsafe(24), "codesentinel-oauth-state", 10)
        response = RedirectResponse(
            "https://github.com/login/oauth/authorize?"
            + urlencode(
                {
                    "client_id": config.github_client_id,
                    "redirect_uri": config.github_oauth_callback_url,
                    "scope": "read:user",
                    "state": state,
                }
            )
        )
        response.set_cookie(
            "codesentinel_oauth_state",
            state,
            max_age=600,
            httponly=True,
            secure=config.environment == "production",
            samesite="lax",
            path="/auth",
        )
        return response

    @router.get("/github/callback")
    def callback(request: Request, code: str, state: str) -> RedirectResponse:
        cookie = request.cookies.get("codesentinel_oauth_state", "")
        if not cookie or not hmac.compare_digest(cookie, state):
            raise ServiceError(
                "OAUTH_STATE_INVALID", "OAuth browser state mismatch", 401
            )
        decode(config, state, "codesentinel-oauth-state")
        try:
            with httpx.Client(
                timeout=15, follow_redirects=False, trust_env=False
            ) as client:
                exchanged = client.post(
                    "https://github.com/login/oauth/access_token",
                    headers={"Accept": "application/json"},
                    json={
                        "client_id": config.github_client_id,
                        "client_secret": config.github_client_secret,
                        "code": code,
                        "redirect_uri": config.github_oauth_callback_url,
                    },
                )
                exchanged.raise_for_status()
                token = exchanged.json()["access_token"]
                user = client.get(
                    "https://api.github.com/user",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github+json",
                    },
                )
                user.raise_for_status()
                subject = str(user.json()["id"])
                if (
                    config.github_allowed_user_ids
                    and subject not in config.github_allowed_user_ids
                ):
                    raise ServiceError(
                        "ACCESS_DENIED",
                        "GitHub user is not allowed for this installation",
                        403,
                    )
                if (
                    config.environment == "production"
                    and not config.github_allowed_user_ids
                ):
                    raise ServiceError(
                        "ACCESS_NOT_CONFIGURED", "Configure allowed GitHub user IDs"
                    )
        except (httpx.HTTPError, KeyError, ValueError):
            raise ServiceError("OAUTH_FAILED", "GitHub OAuth exchange failed") from None
        response = RedirectResponse(
            config.frontend_url.rstrip("/") + "/login#token=" + mint(config, subject)
        )
        response.delete_cookie("codesentinel_oauth_state", path="/auth")
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    return router
