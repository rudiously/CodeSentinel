"""Bounded ASGI request buffering and source-free, uniform error handling."""

import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class ServiceError(Exception):
    def __init__(self, code: str, message: str, status: int = 503) -> None:
        self.code, self.message, self.status = code, message, status
        super().__init__(message)


def error_response(
    code: str, message: str, status: int, request_id: str
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "request_id": request_id}},
        headers={"X-Request-ID": request_id},
    )


class BodyLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        chunks: list[bytes] = []
        size = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            size += len(chunk)
            if size > self.max_bytes:
                await error_response(
                    "INPUT_TOO_LARGE",
                    "Request exceeds configured byte limit",
                    413,
                    scope.get("state", {}).get("request_id", str(uuid4())),
                )(scope, receive, send)
                return
            chunks.append(chunk)
            if not message.get("more_body", False):
                break
        consumed = False

        async def replay() -> Message:
            nonlocal consumed
            if not consumed:
                consumed = True
                return {
                    "type": "http.request",
                    "body": b"".join(chunks),
                    "more_body": False,
                }
            return await receive()

        await self.app(scope, replay, send)


def install_errors(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        return error_response(
            "INVALID_INPUT",
            "Request failed schema validation",
            422,
            getattr(request.state, "request_id", str(uuid4())),
        )

    @app.exception_handler(ServiceError)
    async def service(request: Request, exc: ServiceError) -> JSONResponse:
        return error_response(
            exc.code,
            exc.message,
            exc.status,
            getattr(request.state, "request_id", str(uuid4())),
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        return error_response(
            "HTTP_ERROR",
            "Request rejected",
            exc.status_code,
            getattr(request.state, "request_id", str(uuid4())),
        )

    @app.exception_handler(Exception)
    async def internal(request: Request, exc: Exception) -> JSONResponse:
        logging.getLogger("codesentinel").error(
            "request_failed", extra={"error_type": type(exc).__name__}
        )
        return error_response(
            "INTERNAL_ERROR",
            "Internal service error",
            500,
            getattr(request.state, "request_id", str(uuid4())),
        )
