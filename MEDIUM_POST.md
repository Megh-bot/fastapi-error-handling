# Stop Scattering Error Handling Across Your API — Do This Instead

One of the most common issues I see in REST APIs is inconsistent error responses.

One endpoint returns `{"error": "not found"}`. Another returns `{"message": "User does not exist", "status": 404}`. A third crashes with a raw 500 and an HTML stack trace.

Clients write defensive code for every endpoint. Debugging becomes a guessing game. Onboarding new developers means learning a different error convention for every route.

The fix isn't complicated. It just requires one decision upfront: **every error response in your API will have the same shape, always.**

Here's how to build that with Python and FastAPI.

---

## The contract

Every error response looks like this — no exceptions:

```json
{
  "success": false,
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "User with id '42' not found.",
    "request_id": "a3f1c2d4-...",
    "timestamp": "2026-04-17T10:23:45Z"
  }
}
```

Every success response looks like this:

```json
{
  "success": true,
  "data": { "id": "1", "name": "Alice", "email": "alice@example.com" }
}
```

Clients check `success`. Done. No status code parsing, no guessing which field holds the error message.

---

## Step 1: Define your error codes as an enum

```python
from enum import Enum

class ErrorCode(str, Enum):
    VALIDATION_INVALID_FORMAT      = "VALIDATION_INVALID_FORMAT"
    AUTH_TOKEN_MISSING             = "AUTH_TOKEN_MISSING"
    AUTH_TOKEN_EXPIRED             = "AUTH_TOKEN_EXPIRED"
    AUTHZ_INSUFFICIENT_PERMISSIONS = "AUTHZ_INSUFFICIENT_PERMISSIONS"
    RESOURCE_NOT_FOUND             = "RESOURCE_NOT_FOUND"
    RESOURCE_ALREADY_EXISTS        = "RESOURCE_ALREADY_EXISTS"
    INTERNAL_SERVER_ERROR          = "INTERNAL_SERVER_ERROR"
```

Using `str, Enum` means these serialize directly to strings in JSON — no extra conversion needed. The `DOMAIN_SPECIFIC_ISSUE` format makes errors machine-readable and easy to handle on the client side.

---

## Step 2: Map every code to an HTTP status — once

```python
ERROR_STATUS_MAP: dict[ErrorCode, int] = {
    ErrorCode.VALIDATION_INVALID_FORMAT:      400,
    ErrorCode.AUTH_TOKEN_MISSING:             401,
    ErrorCode.AUTH_TOKEN_EXPIRED:             401,
    ErrorCode.AUTHZ_INSUFFICIENT_PERMISSIONS: 403,
    ErrorCode.RESOURCE_NOT_FOUND:             404,
    ErrorCode.RESOURCE_ALREADY_EXISTS:        409,
    ErrorCode.INTERNAL_SERVER_ERROR:          500,
}
```

This is the single source of truth. No route handler ever hard-codes a status number. Want to change a status code? One-line edit.

---

## Step 3: One exception class for the whole app

```python
class AppError(Exception):
    def __init__(self, code: ErrorCode, message: str = None, details: dict = None):
        self.code = code
        self.status_code = ERROR_STATUS_MAP[code]
        self.message = message or ERROR_MESSAGES[code]
        self.details = details
        super().__init__(self.message)

    @classmethod
    def not_found(cls, message: str = None) -> "AppError":
        return cls(ErrorCode.RESOURCE_NOT_FOUND, message)

    @classmethod
    def forbidden(cls, message: str = None) -> "AppError":
        return cls(ErrorCode.AUTHZ_INSUFFICIENT_PERMISSIONS, message)
```

Factory methods keep route handlers readable:

```python
# Verbose
raise AppError(ErrorCode.RESOURCE_NOT_FOUND, f"User {user_id} not found")

# Clean
raise AppError.not_found(f"User {user_id} not found")
```

---

## Step 4: Three exception handlers cover everything

```python
# 1. Your errors — operational, expected failures
@app.exception_handler(AppError)
async def app_error_handler(request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "request_id": request.state.request_id,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        },
    )

# 2. Pydantic validation — FastAPI raises this automatically for bad request bodies
@app.exception_handler(RequestValidationError)
async def validation_handler(request, exc):
    fields = {
        ".".join(str(l) for l in e["loc"] if l != "body"): e["msg"]
        for e in exc.errors()
    }
    # Same envelope — details.fields contains a field → message map

# 3. Everything else — bugs, infra failures
@app.exception_handler(Exception)
async def generic_handler(request, exc):
    logger.error("Unhandled exception", exc_info=True)
    # Return a generic message — never leak internal details to the client
```

Handler #3 is the most important. It's the difference between a client seeing `"An unexpected error occurred."` and seeing your database connection string in a stack trace.

---

## What this looks like in a route

```python
@router.post("/users")
async def create_user(body: CreateUserRequest):  # Pydantic validates automatically
    if any(u["email"] == body.email for u in users.values()):
        raise AppError(
            ErrorCode.RESOURCE_ALREADY_EXISTS,
            f"A user with email '{body.email}' already exists.",
            details={"field": "email"},
        )
    # ... create user
```

No try/except. No `return JSONResponse(status_code=409, ...)`. Just raise and let the handler do its job.

---

## Pydantic does validation for free

Define constraints on your request model and FastAPI raises `RequestValidationError` automatically. Your handler reformats it into the standard shape:

```python
class CreateUserRequest(BaseModel):
    name: str = Field(..., min_length=2)
    email: EmailStr
    age: Optional[int] = Field(None, ge=0, le=150)
```

A request with `age: 200` returns:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_INVALID_FORMAT",
    "message": "Request validation failed.",
    "details": {
      "fields": {
        "age": "Input should be less than or equal to 150"
      }
    }
  }
}
```

Field-level errors, standard envelope, zero extra code in the route.

---

## The test that matters most

```python
def test_unhandled_exception_returns_500_without_leaking_details():
    res = client.get("/users/trigger-500")
    assert res.status_code == 500
    assert res.json()["error"]["code"] == "INTERNAL_SERVER_ERROR"
    # The important assertion — internal details must never reach the client
    assert "null reference" not in res.json()["error"]["message"]
    assert res.json()["error"]["message"] == "An unexpected error occurred."
```

If this passes, your API never leaks internal details — regardless of what breaks.

---

## The payoff

- **Clients write one error handler** for your entire API
- **Every error is traceable** — paste the `request_id` into your logs and find the full context instantly
- **Adding a new error type is three lines**: add to the enum, add to the status map, add a default message
- **OpenAPI docs are accurate automatically** — Pydantic generates response schemas for every endpoint

The full working code with all 15 tests is [on GitHub](#).

---

*Built this with [Kiro](https://kiro.dev) — asked it to generate standardized error handling for a FastAPI REST API, then walked through the design decisions together.*
