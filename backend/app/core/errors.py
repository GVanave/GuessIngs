"""Consistent, user-friendly error responses. Never leak stack traces."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("app.errors")


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: dict | None = None,
                 headers: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}
        self.headers = headers


def error_body(code: str, message: str, details: dict | None = None) -> dict:
    body: dict = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return body


def _friendly_field(err: dict) -> str:
    loc = [str(p) for p in err.get("loc", []) if p not in ("body", "query", "path")]
    field = loc[-1] if loc else "input"
    msg = err.get("msg", "Invalid value")
    msg = msg.removeprefix("Value error, ")
    return f"{field}: {msg}"


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return JSONResponse(error_body(exc.code, exc.message, exc.details), status_code=exc.status_code,
                            headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        fields = {}
        for err in exc.errors():
            loc = [str(p) for p in err.get("loc", []) if p not in ("body", "query", "path")]
            fields[loc[-1] if loc else "input"] = _friendly_field(err).split(": ", 1)[-1]
        first = next(iter(fields.values()), "Invalid input")
        return JSONResponse(error_body("validation_error", first, {"fields": fields}), status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        messages = {404: "Not found.", 405: "Method not allowed.", 401: "Please sign in.", 403: "Forbidden."}
        message = exc.detail if isinstance(exc.detail, str) and exc.status_code < 500 else messages.get(exc.status_code, "Request failed.")
        return JSONResponse(error_body(f"http_{exc.status_code}", message), status_code=exc.status_code)

    @app.exception_handler(OperationalError)
    async def _db_down(_: Request, exc: OperationalError):
        log.error("Database unavailable: %s", type(exc).__name__)
        return JSONResponse(
            error_body("database_unavailable", "Our database is temporarily unavailable. Please try again shortly."),
            status_code=503,
        )

    @app.exception_handler(SQLAlchemyError)
    async def _db_error(_: Request, exc: SQLAlchemyError):
        log.exception("Database error")
        return JSONResponse(
            error_body("database_error", "We couldn't save or load your data. Please try again."), status_code=500
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        log.exception("Unhandled error")
        return JSONResponse(error_body("internal_error", "Something went wrong on our side. Please try again."),
                            status_code=500)
