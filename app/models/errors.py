"""
Standardized error codes, HTTP status mappings, and response models.

Design decisions:
- ErrorCode is a StrEnum so values serialize to plain strings in JSON responses
  (e.g. "RESOURCE_NOT_FOUND" not "ErrorCode.RESOURCE_NOT_FOUND").
- ERROR_STATUS_MAP is the single source of truth for HTTP status codes.
  No route handler ever hard-codes a status number.
- ApiErrorResponse and ApiSuccessResponse are Pydantic models, so FastAPI
  generates accurate OpenAPI docs for both shapes automatically.
"""

from enum import Enum
from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel


class ErrorCode(str, Enum):
    # Validation (400)
    VALIDATION_REQUIRED_FIELD = "VALIDATION_REQUIRED_FIELD"
    VALIDATION_INVALID_FORMAT = "VALIDATION_INVALID_FORMAT"
    VALIDATION_OUT_OF_RANGE = "VALIDATION_OUT_OF_RANGE"

    # Authentication (401)
    AUTH_TOKEN_MISSING = "AUTH_TOKEN_MISSING"
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    AUTH_TOKEN_INVALID = "AUTH_TOKEN_INVALID"

    # Authorization (403)
    AUTHZ_INSUFFICIENT_PERMISSIONS = "AUTHZ_INSUFFICIENT_PERMISSIONS"
    AUTHZ_RESOURCE_FORBIDDEN = "AUTHZ_RESOURCE_FORBIDDEN"

    # Resource (404 / 409)
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"

    # Rate limiting (429)
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # Server errors (500 / 502)
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"


# Maps every error code to its canonical HTTP status code.
# Centralizing this means changing a status code is a one-line edit.
ERROR_STATUS_MAP: dict[ErrorCode, int] = {
    ErrorCode.VALIDATION_REQUIRED_FIELD: 400,
    ErrorCode.VALIDATION_INVALID_FORMAT: 400,
    ErrorCode.VALIDATION_OUT_OF_RANGE: 400,

    ErrorCode.AUTH_TOKEN_MISSING: 401,
    ErrorCode.AUTH_TOKEN_EXPIRED: 401,
    ErrorCode.AUTH_TOKEN_INVALID: 401,

    ErrorCode.AUTHZ_INSUFFICIENT_PERMISSIONS: 403,
    ErrorCode.AUTHZ_RESOURCE_FORBIDDEN: 403,

    ErrorCode.RESOURCE_NOT_FOUND: 404,
    ErrorCode.RESOURCE_ALREADY_EXISTS: 409,

    ErrorCode.RATE_LIMIT_EXCEEDED: 429,

    ErrorCode.INTERNAL_SERVER_ERROR: 500,
    ErrorCode.DATABASE_ERROR: 500,
    ErrorCode.EXTERNAL_SERVICE_ERROR: 502,
}

# Default human-readable messages. Routes can override with context-specific text.
ERROR_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.VALIDATION_REQUIRED_FIELD: "A required field is missing.",
    ErrorCode.VALIDATION_INVALID_FORMAT: "One or more fields have an invalid format.",
    ErrorCode.VALIDATION_OUT_OF_RANGE: "A field value is outside the allowed range.",

    ErrorCode.AUTH_TOKEN_MISSING: "Authentication token is required.",
    ErrorCode.AUTH_TOKEN_EXPIRED: "Authentication token has expired.",
    ErrorCode.AUTH_TOKEN_INVALID: "Authentication token is invalid.",

    ErrorCode.AUTHZ_INSUFFICIENT_PERMISSIONS: "You do not have permission to perform this action.",
    ErrorCode.AUTHZ_RESOURCE_FORBIDDEN: "Access to this resource is forbidden.",

    ErrorCode.RESOURCE_NOT_FOUND: "The requested resource was not found.",
    ErrorCode.RESOURCE_ALREADY_EXISTS: "A resource with this identifier already exists.",

    ErrorCode.RATE_LIMIT_EXCEEDED: "Too many requests. Please slow down.",

    ErrorCode.INTERNAL_SERVER_ERROR: "An unexpected error occurred.",
    ErrorCode.DATABASE_ERROR: "A database error occurred.",
    ErrorCode.EXTERNAL_SERVICE_ERROR: "An upstream service is unavailable.",
}


# ── Response envelope models ──────────────────────────────────────────────────

class ErrorDetail(BaseModel):
    code: ErrorCode
    message: str
    details: Optional[dict[str, Any]] = None
    request_id: str
    timestamp: str


class ApiErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail


T = TypeVar("T")


class ApiSuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T
    meta: Optional[dict[str, Any]] = None
