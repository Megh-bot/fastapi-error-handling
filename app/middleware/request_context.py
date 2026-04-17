"""
Request context middleware.

Attaches a unique request_id to every request and echoes it back in the
X-Request-ID response header. Downstream handlers and the error handler
read it from request.state.request_id.

Design decisions:
- Checks X-Request-ID header first so API gateways and load balancers can
  inject their own trace IDs (useful for end-to-end tracing in AWS).
- Falls back to a UUID v4 if none is provided.
- Logs request start and response finish with duration for basic observability.
"""

import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.utils.logger import log_request, log_response


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id

        log_request(request.method, request.url.path, request_id)

        start = time.monotonic()
        response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000, 2)

        response.headers["X-Request-ID"] = request_id
        log_response(request.method, request.url.path, response.status_code, request_id, duration_ms)

        return response
