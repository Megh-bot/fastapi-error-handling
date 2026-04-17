"""
AppError — the single exception class used throughout the application.

Design decisions:
- Subclasses Exception so it can be raised anywhere and caught by FastAPI's
  exception handler or a plain try/except.
- Carries an ErrorCode so the handler resolves the HTTP status from
  ERROR_STATUS_MAP — no status numbers scattered across route handlers.
- `is_operational` separates expected failures (validation, not found) from
  unexpected ones (bugs, infra). The handler exposes details for operational
  errors and returns a generic 500 for non-operational ones.
- Factory class methods keep raise sites readable:
    raise AppError.not_found(f"User {user_id} not found")
  instead of:
    raise AppError(ErrorCode.RESOURCE_NOT_FOUND, f"User {user_id} not found")
"""

from typing import Any, Optional
from app.models.errors import ErrorCode, ERROR_STATUS_MAP, ERROR_MESSAGES


class AppError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        is_operational: bool = True,
    ):
        self.code = code
        self.status_code = ERROR_STATUS_MAP[code]
        self.message = message or ERROR_MESSAGES[code]
        self.details = details
        self.is_operational = is_operational
        super().__init__(self.message)

    # ── Factory helpers ───────────────────────────────────────────────────────

    @classmethod
    def not_found(cls, message: Optional[str] = None, details: Optional[dict] = None) -> "AppError":
        return cls(ErrorCode.RESOURCE_NOT_FOUND, message, details)

    @classmethod
    def validation_error(cls, message: Optional[str] = None, details: Optional[dict] = None) -> "AppError":
        return cls(ErrorCode.VALIDATION_INVALID_FORMAT, message, details)

    @classmethod
    def unauthorized(cls, code: ErrorCode = ErrorCode.AUTH_TOKEN_MISSING) -> "AppError":
        return cls(code)

    @classmethod
    def forbidden(cls, message: Optional[str] = None) -> "AppError":
        return cls(ErrorCode.AUTHZ_INSUFFICIENT_PERMISSIONS, message)

    @classmethod
    def internal(cls, message: Optional[str] = None) -> "AppError":
        # Non-operational: details are never exposed to the client
        return cls(ErrorCode.INTERNAL_SERVER_ERROR, message, is_operational=False)
