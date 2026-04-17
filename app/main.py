"""
Application factory.

Registers middleware and exception handlers in the correct order:
1. RequestContextMiddleware — runs first on the way in, last on the way out
2. Exception handlers — FastAPI matches most-specific to least-specific
3. Routers
"""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.middleware.request_context import RequestContextMiddleware
from app.middleware.error_handlers import (
    app_error_handler,
    validation_error_handler,
    generic_error_handler,
)
from app.routes.users import router as users_router
from app.utils.app_error import AppError

app = FastAPI(
    title="API Error Handling Demo",
    description="Standardized error codes, messages, and HTTP status codes across all endpoints.",
    version="1.0.0",
)

# Middleware
app.add_middleware(RequestContextMiddleware)

# Exception handlers — order matters: most specific first
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(Exception, generic_error_handler)

# Routes
app.include_router(users_router)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}
