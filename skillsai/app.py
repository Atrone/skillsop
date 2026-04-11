"""FastAPI backend exposing the SkillsAI federation gateway. """

from __future__ import annotations

import os
import sys
import types
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from .models import PlatformRequest
    from .seed_loader import load_seed_data
    from .skills_platform import SkillsAIPlatform
except ImportError:
    from .models import PlatformRequest
    from .seed_loader import load_seed_data
    from .skills_platform import SkillsAIPlatform


class PlatformRequestModel(BaseModel):
    """HTTP request model for one federation gateway call."""

    method: str = Field(min_length=1)
    path: str = Field(min_length=1)
    actor_id: str = Field(min_length=1)
    token: str = Field(min_length=1)
    payload: Dict[str, Any] = Field(default_factory=dict)


class PlatformResponseModel(BaseModel):
    """HTTP response model returned from gateway execution."""

    status_code: int
    body: Dict[str, Any]
    audit_id: str


class HealthResponseModel(BaseModel):
    """Health check payload for API readiness checks."""

    status: str
    service: str


# Block comment:
# This helper parses comma-separated CORS origins from environment settings.
def read_cors_origins() -> List[str]:
    """Read allowed CORS origins for browser-based frontend clients."""
    # Line comment: use local frontend defaults when explicit origins are not configured.
    raw_origins = os.getenv(
        "SKILLSAI_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    # Line comment: trim whitespace and remove empty origin segments.
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


# Block comment:
# This helper seeds deterministic fallback data when seed-data is unavailable.
def seed_demo_data(platform: SkillsAIPlatform) -> None:
    """Seed identity and assessment data when the seed-data folder is unavailable."""
    # Line comment: ensure default employee identity exists for query-path demos.
    if "identity:emp-1" not in platform.stores.cache:
        platform.identity_mapper.upsert_identity(
            "emp-1",
            {"tenant_id": "default-tenant", "roles": ["employee"]},
        )
    # Line comment: publish default assessment package used by command-path forms.
    if "asm-1" not in platform.stores.item_bank:
        platform.assessments.publish_assessment(
            "asm-1",
            definition={
                "sections": [{"name": "Foundations"}],
                "items": [{"id": "q1", "skill_id": "skill:asm-1"}],
                "rubric": {"type": "binary"},
            },
        )


# Block comment:
# This function builds the FastAPI app and wires it to the platform gateway.
def create_app() -> FastAPI:
    """Create an initialized FastAPI application for SkillsAI APIs."""
    # Line comment: create app shell with metadata for API documentation.
    app = FastAPI(title="SkillsAI API", version="0.1.0")
    # Line comment: compose the architecture platform and keep it in app state.
    app.state.platform = SkillsAIPlatform()
    # Line comment: hydrate stores from the shared seed-data folder when it is present.
    load_seed_data(app.state.platform)
    # Line comment: preserve a minimal fallback dataset when the seed-data folder is unavailable.
    if not bool(app.state.platform.stores.meta.get("seed_data_loaded", False)):
        seed_demo_data(app.state.platform)
    # Line comment: enable browser calls from the React dev server origin.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=read_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Block comment:
    # This endpoint exposes liveness/readiness information for the backend.
    @app.get("/api/v1/health", response_model=HealthResponseModel)
    def health() -> HealthResponseModel:
        """Return backend health metadata for local verification."""
        # Line comment: return a fixed healthy response payload.
        return HealthResponseModel(status="ok", service="skillsai-backend")

    # Block comment:
    # This endpoint forwards generic gateway requests to SkillsAI domain logic.
    @app.post("/api/v1/platform/request", response_model=PlatformResponseModel)
    def handle_platform_request(request: PlatformRequestModel) -> PlatformResponseModel:
        """Handle one platform gateway request through the architecture pipeline."""
        # Line comment: adapt pydantic HTTP payload into internal dataclass request.
        platform_request = PlatformRequest(
            method=request.method,
            path=request.path,
            actor_id=request.actor_id,
            token=request.token,
            payload=request.payload,
        )
        # Line comment: route the request through composed gateway with mapped errors.
        try:
            response = app.state.platform.gateway.handle_request(platform_request)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=f"Invalid request payload: {exc}") from exc
        # Line comment: normalize internal dataclass response to pydantic payload.
        return PlatformResponseModel(
            status_code=response.status_code,
            body=response.body,
            audit_id=response.audit_id,
        )

    return app


app = create_app()
