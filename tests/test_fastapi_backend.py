"""Tests for the SkillsAI FastAPI backend adapter."""

from fastapi.testclient import TestClient

from skillsai.api import create_app


# Block comment:
# This helper builds a test client bound to a fresh FastAPI application.
def build_client() -> TestClient:
    """Create a test client for backend endpoint contract validation."""
    # Line comment: construct a new app instance to isolate test state.
    app = create_app()
    # Line comment: return a synchronous client for API route execution.
    return TestClient(app)


# Block comment:
# This test verifies the health route returns expected readiness metadata.
def test_health_endpoint_returns_ok() -> None:
    """Ensure health endpoint responds with stable service payload."""
    # Line comment: create a client and issue a health request.
    client = build_client()
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    # Line comment: verify payload fields expected by operational checks.
    assert response.json() == {"status": "ok", "service": "skillsai-backend"}


# Block comment:
# This test verifies frontend-facing platform endpoint contract is operational.
def test_platform_request_endpoint_returns_gateway_response() -> None:
    """Ensure POST platform request returns status, body, and audit id."""
    # Line comment: create a client and send one analytics gateway request.
    client = build_client()
    response = client.post(
        "/api/v1/platform/request",
        json={
            "method": "GET",
            "path": "/analytics",
            "actor_id": "emp-1",
            "token": "valid-token",
            "payload": {
                "metric": "skill_coverage",
                "cohort": "all",
                "start": "2026-01-01",
                "end": "2026-12-31",
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    # Line comment: validate envelope fields consumed by frontend JSON renderer.
    assert data["status_code"] == 200
    assert data["body"]["status"] == "ok"
    assert "audit_id" in data and data["audit_id"].startswith("audit-")


# Block comment:
# This test verifies the backend loads seeded identity data from the seed-data folder.
def test_platform_request_endpoint_returns_seeded_identity() -> None:
    """Ensure the identity query returns the seeded employee profile."""
    # Line comment: create a client and request the canonical seeded identity.
    client = build_client()
    response = client.post(
        "/api/v1/platform/request",
        json={
            "method": "GET",
            "path": "/identity",
            "actor_id": "emp-1",
            "token": "emp-1:default",
            "payload": {
                "employee_id": "emp-1",
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    # Line comment: validate the seed-data identity payload is exposed through the gateway.
    assert data["body"]["data"]["identity"]["actor_id"] == "emp-1"
    assert data["body"]["data"]["identity"]["tenant_id"] == "default-tenant"


# Block comment:
# This test verifies assessment queries can return both package and attempt seed data.
def test_platform_request_endpoint_returns_seeded_assessment_workspace() -> None:
    """Ensure assessment query returns the seeded package and seeded attempt."""
    # Line comment: create a client and request both assessment package and attempt state.
    client = build_client()
    response = client.post(
        "/api/v1/platform/request",
        json={
            "method": "GET",
            "path": "/assessments",
            "actor_id": "emp-1",
            "token": "emp-1:default",
            "payload": {
                "assessment_id": "asm-1",
                "attempt_id": "attempt-1",
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    # Line comment: validate both seeded assessment package metadata and attempt state are returned.
    assert data["body"]["data"]["assessment"]["assessment_id"] == "asm-1"
    assert data["body"]["data"]["assessment_attempt"]["session"]["attempt_id"] == "attempt-1"


# Block comment:
# This test verifies the backend exposes seed-data module metadata for admin views.
def test_platform_request_endpoint_returns_seeded_admin_summary() -> None:
    """Ensure admin query returns the seed-data loading summary."""
    # Line comment: create a client and request backend admin metadata.
    client = build_client()
    response = client.post(
        "/api/v1/platform/request",
        json={
            "method": "GET",
            "path": "/admin",
            "actor_id": "manager-1",
            "token": "manager-1:default",
            "payload": {},
        },
    )
    assert response.status_code == 200
    data = response.json()
    # Line comment: validate seed module metadata expected by the frontend admin page.
    assert "identity" in data["body"]["data"]["admin"]["seed_modules"]
    assert data["body"]["data"]["admin"]["assessment_ids"] == ["asm-1"]


# Block comment:
# This test verifies backend validation behavior for malformed command payloads.
def test_platform_request_endpoint_rejects_invalid_payload() -> None:
    """Ensure POST platform request returns 400 on invalid command payload."""
    # Line comment: send malformed inference payload with non-numeric value.
    client = build_client()
    response = client.post(
        "/api/v1/platform/request",
        json={
            "method": "POST",
            "path": "/command/core/infer",
            "actor_id": "emp-1",
            "token": "valid-token",
            "payload": {
                "employee_id": "emp-1",
                "skill_id": "skill:python",
                "value": "not-a-number",
            },
        },
    )
    assert response.status_code == 400
    # Line comment: validate response provides actionable error details.
    assert "Invalid request payload" in response.json()["detail"]
