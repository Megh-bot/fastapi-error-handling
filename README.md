# FastAPI Error Handling

Standardized error codes, messages, and HTTP status codes across every endpoint — built with Python and FastAPI.

Every error response from this API has the same shape, always:

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

Read the full write-up on [Medium](#).

---

## Project structure

```
app/
├── main.py                      # App factory, registers middleware + handlers
├── models/
│   └── errors.py                # ErrorCode enum, status map, Pydantic response models
├── middleware/
│   ├── request_context.py       # Attaches request_id to every request, logs timing
│   └── error_handlers.py        # 3 handlers: AppError, Pydantic validation, generic
├── routes/
│   └── users.py                 # Demo routes covering every error type
└── utils/
    ├── app_error.py             # AppError class with factory helpers
    └── logger.py                # Structured logger (JSON in prod, readable in dev)
tests/
└── test_error_handling.py       # 15 integration tests
```

---

## Setup

Requires Python 3.10–3.12.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Run the tests

```bash
pytest tests/ -v
```

Expected output:

```
PASSED  test_missing_required_fields_returns_400
PASSED  test_invalid_email_returns_400
PASSED  test_short_name_returns_400
PASSED  test_age_out_of_range_returns_400
PASSED  test_delete_without_auth_returns_401_token_missing
PASSED  test_delete_with_expired_token_returns_401_token_expired
PASSED  test_delete_with_forbidden_flag_returns_403
PASSED  test_get_nonexistent_user_returns_404
PASSED  test_unknown_route_returns_404
PASSED  test_duplicate_email_returns_409
PASSED  test_unhandled_exception_returns_500_without_leaking_details
PASSED  test_provided_request_id_is_echoed_in_header_and_body
PASSED  test_request_id_is_auto_generated_when_not_provided
PASSED  test_get_existing_user_returns_200
PASSED  test_create_valid_user_returns_201

15 passed in 0.64s
```

---

## Run the server

```bash
uvicorn app.main:app --reload
```

Interactive API docs at [http://localhost:8000/docs](http://localhost:8000/docs).

---

## Error codes

| Code | Status | When |
|---|---|---|
| `VALIDATION_INVALID_FORMAT` | 400 | Request body fails Pydantic validation |
| `VALIDATION_REQUIRED_FIELD` | 400 | Required field is missing |
| `VALIDATION_OUT_OF_RANGE` | 400 | Field value outside allowed range |
| `AUTH_TOKEN_MISSING` | 401 | No Authorization header |
| `AUTH_TOKEN_EXPIRED` | 401 | Token has expired |
| `AUTH_TOKEN_INVALID` | 401 | Token is malformed or invalid |
| `AUTHZ_INSUFFICIENT_PERMISSIONS` | 403 | Authenticated but not authorized |
| `AUTHZ_RESOURCE_FORBIDDEN` | 403 | Access to resource is forbidden |
| `RESOURCE_NOT_FOUND` | 404 | Resource does not exist |
| `RESOURCE_ALREADY_EXISTS` | 409 | Duplicate resource |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_SERVER_ERROR` | 500 | Unhandled exception |
| `DATABASE_ERROR` | 500 | Database failure |
| `EXTERNAL_SERVICE_ERROR` | 502 | Upstream service unavailable |

---

## Adding a new error type

1. Add the code to `ErrorCode` in `app/models/errors.py`
2. Add its HTTP status to `ERROR_STATUS_MAP`
3. Add a default message to `ERROR_MESSAGES`

That's it. The error handler picks it up automatically.
