"""Tests for the Python implementation of the architecture docs."""
from __future__ import annotations
from pathlib import Path
import sys
import importlib

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

sys.modules.pop("skillsai", None)
api_module = importlib.import_module("skillsai.app")

from skillsai.models import PlatformRequest
from skillsai.skills_platform import SkillsAIPlatform


# Block comment:
# This helper builds a ready-to-use platform fixture for integration-style tests.
def build_platform() -> SkillsAIPlatform:
    """Create a platform instance with in-memory stores."""
    # Line comment: instantiate the end-to-end platform wiring.
    return SkillsAIPlatform()


# Block comment:
# This test validates federation command flow into assessments and then core inference.
def test_assessment_submission_flows_into_inference() -> None:
    """Ensure assessment events publish evidence and update inferred skill state."""
    # Line comment: create platform and publish one assessment with skill mappings.
    platform = build_platform()
    platform.assessments.publish_assessment(
        "asm-1",
        definition={
            "sections": [{"name": "Data Literacy Check"}],
            "items": [
                {"id": "q1", "skill_id": "skill:data-literacy"},
                {"id": "q2", "skill_id": "skill:data-literacy"},
            ],
            "rubric": {"type": "binary"},
        },
    )
    # Line comment: execute submission through the federation command path.
    response = platform.federation_gateway.handle(
        PlatformRequest(
            method="POST",
            path="/command/assessments/submit",
            actor_id="emp-1",
            token="valid-token",
            payload={
                "attempt_id": "attempt-1",
                "assessment_id": "asm-1",
                "employee_id": "emp-1",
                "responses": {"q1": 1, "q2": 0},
            },
        )
    )
    assert response.status_code == 200
    # Line comment: confirm attempt, score, and inferred state were all persisted.
    attempt = platform.stores.attempts["attempt-1"]
    assert "final" in attempt["scores"]
    inferred_key = "emp-1:skill:asm-1"
    assert inferred_key in platform.stores.graph
    assert platform.stores.graph[inferred_key]["proficiency"] >= 0.0


# Block comment:
# This test validates query flow for analytics API and dashboard generation.
def test_analytics_query_returns_dashboard_payload() -> None:
    """Ensure analytics query path renders a dashboard payload."""
    # Line comment: set up base mart metric and warehouse history.
    platform = build_platform()
    platform.stores.mart["skill_coverage:all"] = 0.82
    platform.stores.warehouse.append({"metric": "skill_coverage", "cohort": "all", "value": 0.80})
    # Line comment: execute a read request routed through query composer.
    response = platform.federation_gateway.handle(
        PlatformRequest(
            method="GET",
            path="/analytics",
            actor_id="analyst-1",
            token="valid-token",
            payload={
                "metric": "skill_coverage",
                "cohort": "all",
                "start": "2026-01-01",
                "end": "2026-12-31",
            },
        )
    )
    assert response.status_code == 200
    analytics_data = response.body["data"]["analytics"]
    assert analytics_data["data"]["value"] == 0.82
    assert analytics_data["metric"] == "skill_coverage"


# Block comment:
# This test validates scheduler-triggered KPI materialization from event-bus refresh.
def test_event_bus_refresh_triggers_snapshot_materialization() -> None:
    """Ensure refresh events trigger scheduler and warehouse publication."""
    # Line comment: seed metric definition and source event history.
    platform = build_platform()
    platform.stores.meta["kpi_definitions"] = {"skill_coverage": {"multiplier": 1.0, "cohort": "all"}}
    platform.stores.time_series.append(
        {
            "event_type": "AssessmentEvidenceEvent",
            "employee_id": "emp-2",
            "skill_id": "skill:python",
            "value": 1.0,
        }
    )
    # Line comment: emit refresh trigger and assert dimensional publication exists.
    platform.event_bus.publish("SkillStateUpdated", {"reason": "assessment-published"})
    assert len(platform.stores.warehouse) > 0
    assert platform.stores.warehouse[-1]["metric"] == "skill_coverage"
