"""
Structured logger.

Uses Python's standard `logging` module configured to emit JSON in production
and human-readable text in development. Swap the handler for structlog,
python-json-logger, or AWS Lambda Powertools Logger with no changes to call sites.

Every log entry carries:
- level, message, timestamp (standard)
- request_id for distributed tracing
- error_code, status_code, path, method for error entries
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional


class JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON for log aggregation pipelines."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        # Merge any extra fields passed via the `extra` kwarg
        for key, value in record.__dict__.items():
            if key not in (
                "args", "asctime", "created", "exc_info", "exc_text", "filename",
                "funcName", "id", "levelname", "levelno", "lineno", "module",
                "msecs", "message", "msg", "name", "pathname", "process",
                "processName", "relativeCreated", "stack_info", "thread", "threadName",
            ):
                log_entry[key] = value
        return json.dumps(log_entry)


def _build_logger() -> logging.Logger:
    logger = logging.getLogger("api")
    logger.setLevel(logging.DEBUG)

    handler = logging.StreamHandler()
    if os.getenv("ENV", "development") == "production":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("[%(levelname)s] %(message)s")
        )

    logger.addHandler(handler)
    logger.propagate = False
    return logger


logger = _build_logger()


def log_request(method: str, path: str, request_id: str) -> None:
    logger.info(f"{method} {path}", extra={"request_id": request_id})


def log_response(method: str, path: str, status_code: int, request_id: str, duration_ms: float) -> None:
    logger.info(
        f"{method} {path} → {status_code}",
        extra={"request_id": request_id, "status_code": status_code, "duration_ms": duration_ms},
    )


def log_error(
    message: str,
    request_id: str,
    error_code: Optional[str] = None,
    status_code: Optional[int] = None,
    path: Optional[str] = None,
    method: Optional[str] = None,
    exc_info: bool = False,
) -> None:
    level = logging.WARNING if status_code and status_code < 500 else logging.ERROR
    logger.log(
        level,
        message,
        exc_info=exc_info,
        extra={
            "request_id": request_id,
            "error_code": error_code,
            "status_code": status_code,
            "path": path,
            "method": method,
        },
    )
