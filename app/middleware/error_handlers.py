"""
Central exception handlers registered on the FastAPI app.

Design decisions:

1. Three handlers cover all cases:
   - app_error_handler   → our AppError (operational errors)
   - validation_handler  → Pydantic's RequestValidationError (automatic for request bodies)
   - generic_handler     → any other Exception (bugs, unhandled failures)

2. Pydantic validation is free — FastAPI validates request bodies against
   Pydantic models automatically and raises RequestValidationError. We intercept
   it here to reformat it into our standard ApiErrorResponse shape instead of
   FastAPI's default {"detail": [...]} format.

3. Non-operational errors (bugs) return a generic 500. The real error is logged
   with exc_info=True so the full traceback appears in logs, but nothing leaks
   to the client.

4. request_id is read from request.state (set by RequestContextMiddleware).
   Every error response includes it so clients can correlate with server logs.
"""

import traceback
from datetime import datetime, timezone

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.models.errors import (
    ApiErrorResponse,
    ErrorCode,
    ERROR_MESSAGES,
    ErrorDetail,
)
from app.utils.app_error import AppError
from app.utils.logger import log_error


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handles all AppError instances — operational, expected failures."""
    request_id = _request_id(request)

    log_error(
        exc.message,
        request_id=request_id,
        error_code=exc.code.value,
        status_code=exc.status_code,
        path=request.url.path,
        method=request.method,
    )

    body = ApiErrorResponse(
        error=ErrorDetail(
            code=exc.code,
            message=exc.message,
            details=exc.details,
            request_id=request_id,
            timestamp=_now(),
        )
    )

    return JSONResponse(status_code=exc.status_code, content=body.model_dump())


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Reformats Pydantic's RequestValidationError into our standard shape.

    Pydantic returns a list of error objects; we flatten them into a
    field -> message dict so clients get a consistent structure regardless
    of whether validation failed in a route handler or at the Pydantic layer.
    """
    request_id = _request_id(request)

    fields: dict[str, str] = {}
    for error in exc.errors():
        # loc is a tuple like ("body", "email") — join to get "email"
        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        fields[field] = error["msg"]

    log_error(
        "Request validation failed",
        request_id=request_id,
        error_code=ErrorCode.VALIDATION_INVALID_FORMAT.value,
        status_code=400,
        path=request.url.path,
        method=request.method,
    )

    body = ApiErrorResponse(
        error=ErrorDetail(
            code=ErrorCode.VALIDATION_INVALID_FORMAT,
            message="Request validation failed.",
            details={"fields": fields},
            request_id=request_id,
            timestamp=_now(),
        )
    )

    return JSONResponse(status_code=400, content=body.model_dump())


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catches any unhandled exception — bugs, infra failures, etc.
    Logs the full traceback but returns a generic 500 to the client.
    """
    request_id = _request_id(request)

    log_error(
        f"Unhandled exception: {exc}",
        request_id=request_id,
        status_code=500,
        path=request.url.path,
        method=request.method,
        exc_info=True,
    )

    body = ApiErrorResponse(
        error=ErrorDetail(
            code=ErrorCode.INTERNAL_SERVER_ERROR,
            message=ERROR_MESSAGES[ErrorCode.INTERNAL_SERVER_ERROR],
            request_id=request_id,
            timestamp=_now(),
        )
    )

    return JSONResponse(status_code=500, content=body.model_dump())
