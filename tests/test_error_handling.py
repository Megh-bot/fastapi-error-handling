"""
Integration tests for standardized error handling.

Each test verifies:
- Correct HTTP status code
- Correct ErrorCode in the response body
- Standard ApiErrorResponse envelope shape
- request_id present in both body and X-Request-ID header
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def assert_error_shape(body: dict, expected_code: str):
    """Helper: assert the response has the standard error envelope."""
    assert body["success"] is False
    assert "error" in body
    error = body["error"]
    assert error["code"] == expected_code
    assert isinstance(error["message"], str)
    assert isinstance(error["request_id"], str)
    assert isinstance(error["timestamp"], str)


# ── 400 Validation ────────────────────────────────────────────────────────────

def test_missing_required_fields_returns_400():
    res = client.post("/users", json={})
    assert res.status_code == 400
    assert_error_shape(res.json(), "VALIDATION_INVALID_FORMAT")
    fields = res.json()["error"]["details"]["fields"]
    assert "name" in fields
    assert "email" in fields


def test_invalid_email_returns_400():
    res = client.post("/users", json={"name": "Charlie", "email": "not-an-email"})
    assert res.status_code == 400
    assert_error_shape(res.json(), "VALIDATION_INVALID_FORMAT")
    assert "email" in res.json()["error"]["details"]["fields"]


def test_short_name_returns_400():
    res = client.post("/users", json={"name": "A", "email": "valid@example.com"})
    assert res.status_code == 400
    fields = res.json()["error"]["details"]["fields"]
    assert "name" in fields


def test_age_out_of_range_returns_400():
    res = client.post("/users", json={"name": "Charlie", "email": "c@example.com", "age": 200})
    assert res.status_code == 400
    fields = res.json()["error"]["details"]["fields"]
    assert "age" in fields


# ── 401 Authentication ────────────────────────────────────────────────────────

def test_delete_without_auth_returns_401_token_missing():
    res = client.delete("/users/1")
    assert res.status_code == 401
    assert_error_shape(res.json(), "AUTH_TOKEN_MISSING")


def test_delete_with_expired_token_returns_401_token_expired():
    res = client.delete("/users/1?expired=true", headers={"Authorization": "Bearer old-token"})
    assert res.status_code == 401
    assert_error_shape(res.json(), "AUTH_TOKEN_EXPIRED")


# ── 403 Authorization ─────────────────────────────────────────────────────────

def test_delete_with_forbidden_flag_returns_403():
    res = client.delete("/users/1?forbidden=true", headers={"Authorization": "Bearer valid-token"})
    assert res.status_code == 403
    assert_error_shape(res.json(), "AUTHZ_INSUFFICIENT_PERMISSIONS")


# ── 404 Not Found ─────────────────────────────────────────────────────────────

def test_get_nonexistent_user_returns_404():
    res = client.get("/users/999")
    assert res.status_code == 404
    assert_error_shape(res.json(), "RESOURCE_NOT_FOUND")
    assert "999" in res.json()["error"]["message"]


def test_unknown_route_returns_404():
    res = client.get("/nonexistent-route")
    assert res.status_code == 404


# ── 409 Conflict ──────────────────────────────────────────────────────────────

def test_duplicate_email_returns_409():
    res = client.post("/users", json={"name": "Duplicate Alice", "email": "alice@example.com"})
    assert res.status_code == 409
    assert_error_shape(res.json(), "RESOURCE_ALREADY_EXISTS")


# ── 500 Internal ──────────────────────────────────────────────────────────────

def test_unhandled_exception_returns_500_without_leaking_details():
    res = client.get("/users/trigger-500")
    assert res.status_code == 500
    assert_error_shape(res.json(), "INTERNAL_SERVER_ERROR")
    # Internal error message must NOT be exposed to the client
    assert "null reference" not in res.json()["error"]["message"]
    assert res.json()["error"]["message"] == "An unexpected error occurred."


# ── Request ID threading ──────────────────────────────────────────────────────

def test_provided_request_id_is_echoed_in_header_and_body():
    res = client.get("/users/999", headers={"X-Request-ID": "trace-abc-123"})
    assert res.headers["x-request-id"] == "trace-abc-123"
    assert res.json()["error"]["request_id"] == "trace-abc-123"


def test_request_id_is_auto_generated_when_not_provided():
    res = client.get("/users/999")
    body_request_id = res.json()["error"]["request_id"]
    assert body_request_id
    assert res.headers["x-request-id"] == body_request_id


# ── Happy path ────────────────────────────────────────────────────────────────

def test_get_existing_user_returns_200():
    res = client.get("/users/1")
    assert res.status_code == 200
    assert res.json()["success"] is True
    assert res.json()["data"]["name"] == "Alice"


def test_create_valid_user_returns_201():
    res = client.post("/users", json={"name": "Diana", "email": "diana@example.com", "age": 28})
    assert res.status_code == 201
    assert res.json()["success"] is True
    assert res.json()["data"]["email"] == "diana@example.com"
