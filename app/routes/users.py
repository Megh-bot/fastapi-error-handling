"""
Users router — demonstrates every error type in realistic scenarios.
"""

from typing import Optional
from fastapi import APIRouter, Header, Query
from pydantic import BaseModel, EmailStr, Field

from app.models.errors import ApiSuccessResponse, ErrorCode
from app.utils.app_error import AppError

router = APIRouter(prefix="/users", tags=["users"])

# In-memory store for demo purposes
_users: dict[str, dict] = {
    "1": {"id": "1", "name": "Alice", "email": "alice@example.com", "age": 30},
    "2": {"id": "2", "name": "Bob", "email": "bob@example.com"},
}


# ── Request / Response models ─────────────────────────────────────────────────

class CreateUserRequest(BaseModel):
    """
    Pydantic validates this automatically when the route receives a request.
    Invalid fields raise RequestValidationError, caught by validation_error_handler.
    Field constraints (min_length, pattern) generate field-level error messages.
    """
    name: str = Field(..., min_length=2, description="User's full name")
    email: EmailStr = Field(..., description="Valid email address")
    age: Optional[int] = Field(None, ge=0, le=150, description="Age between 0 and 150")


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    age: Optional[int] = None


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/trigger-500", include_in_schema=True)
async def trigger_500():
    """
    Demonstrates: unhandled exception → generic 500, no internal details leaked.
    Must be registered before /{user_id} so FastAPI matches it as a static route.
    """
    raise RuntimeError("Unexpected null reference in user service")


@router.get("/{user_id}", response_model=ApiSuccessResponse[UserResponse])
async def get_user(user_id: str):
    """
    Demonstrates: RESOURCE_NOT_FOUND
    """
    user = _users.get(user_id)
    if not user:
        raise AppError.not_found(f"User with id '{user_id}' not found.")
    return ApiSuccessResponse(data=UserResponse(**user))


@router.post("/", response_model=ApiSuccessResponse[UserResponse], status_code=201)
async def create_user(body: CreateUserRequest):
    """
    Demonstrates: VALIDATION errors (handled by Pydantic automatically)
                  RESOURCE_ALREADY_EXISTS
    """
    # Check for duplicate email
    if any(u["email"] == body.email for u in _users.values()):
        raise AppError(
            ErrorCode.RESOURCE_ALREADY_EXISTS,
            f"A user with email '{body.email}' already exists.",
            details={"field": "email"},
        )

    new_id = str(len(_users) + 1)
    new_user = {"id": new_id, "name": body.name, "email": body.email}
    if body.age is not None:
        new_user["age"] = body.age
    _users[new_id] = new_user

    return ApiSuccessResponse(data=UserResponse(**new_user))


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    authorization: Optional[str] = Header(None),
    expired: bool = Query(False, description="Demo: simulate expired token"),
    forbidden: bool = Query(False, description="Demo: simulate insufficient permissions"),
):
    """
    Demonstrates: AUTH_TOKEN_MISSING, AUTH_TOKEN_EXPIRED, AUTHZ_INSUFFICIENT_PERMISSIONS
    """
    if not authorization:
        raise AppError.unauthorized(ErrorCode.AUTH_TOKEN_MISSING)

    if expired:
        raise AppError.unauthorized(ErrorCode.AUTH_TOKEN_EXPIRED)

    if forbidden:
        raise AppError.forbidden("Only admins can delete users.")

    user = _users.get(user_id)
    if not user:
        raise AppError.not_found(f"User with id '{user_id}' not found.")

    del _users[user_id]



