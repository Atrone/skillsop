"""Domain models for the SkillsAI architecture implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PlatformRequest:
    """Represents one inbound request at the federation gateway."""

    method: str
    path: str
    actor_id: str
    token: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RequestContext:
    """Represents resolved session context for one tenant-scoped request."""

    actor_id: str
    tenant_id: str
    roles: list[str]
    claims: dict[str, Any]
    feature_flags: dict[str, bool]


@dataclass(slots=True)
class PlatformResponse:
    """Represents normalized response envelope returned by the gateway."""

    status_code: int
    body: dict[str, Any]
    audit_id: str


@dataclass(slots=True)
class EvidenceSignal:
    """Represents one normalized signal used by inference."""

    employee_id: str
    skill_id: str
    value: float
    source: str
    confidence_hint: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SkillState:
    """Represents inferred current state for an employee-skill pair."""

    employee_id: str
    skill_id: str
    proficiency: float
    confidence: float
    gap: float
    explanation: str
    model_version: str


@dataclass(slots=True)
class AssessmentSubmission:
    """Represents an assessment attempt submission payload."""

    attempt_id: str
    assessment_id: str
    employee_id: str
    responses: dict[str, Any]


@dataclass(slots=True)
class KPIQuery:
    """Represents an analytics query from manager or analyst."""

    metric: str
    cohort: str
    start: str
    end: str

