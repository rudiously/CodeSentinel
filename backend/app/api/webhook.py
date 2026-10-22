import json
import re
from typing import Any

from fastapi import APIRouter, Request
from starlette.concurrency import run_in_threadpool

from backend.app.core.security import DeliveryCache, verify_webhook
from shared.http import ServiceError


def webhook_router(secret: str) -> APIRouter:
    router = APIRouter()
    deliveries = DeliveryCache()

    @router.post("/webhook/github")
    async def webhook(request: Request) -> dict[str, Any]:
        raw = await request.body()
        verify_webhook(raw, request.headers.get("X-Hub-Signature-256"), secret)
        if request.headers.get("X-GitHub-Event") != "pull_request":
            return {"status": "ignored"}
        try:
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("Expected object")
            if payload.get("action") not in {"opened", "synchronize", "reopened"}:
                return {"status": "ignored"}
            number = payload["number"]
            repository = payload["repository"]["full_name"]
            sha = payload["pull_request"]["head"]["sha"]
            if (
                type(number) is not int
                or number <= 0
                or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository)
                or not re.fullmatch(r"[a-fA-F0-9]{40,64}", sha)
            ):
                raise ValueError("Invalid PR identity")
        except (ValueError, KeyError, TypeError):
            raise ServiceError(
                "INVALID_WEBHOOK", "Invalid pull request payload", 422
            ) from None
        delivery = request.headers.get("X-GitHub-Delivery", "")
        if not re.fullmatch(r"[A-Za-z0-9-]{1,100}", delivery):
            raise ServiceError(
                "INVALID_DELIVERY", "A valid delivery identifier is required", 422
            )
        if not deliveries.begin(delivery):
            return {"status": "duplicate"}
        try:
            handler = getattr(request.app.state, "github_handler", None)
            if handler is None:
                raise ServiceError(
                    "GITHUB_NOT_CONFIGURED", "GitHub App integration is not configured"
                )
            return await run_in_threadpool(handler, repository, number, sha)
        except Exception:
            deliveries.forget(delivery)
            raise

    return router
