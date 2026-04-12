"""Focused tests for background workflow orchestration and job status queries."""

from __future__ import annotations

from skillsai.models import PlatformRequest
from skillsai.skills_platform import SkillsAIPlatform
from skillsai.stores import PlatformStores
from skillsai.workflow_orchestration import WorkflowOrchestrationService


# Block comment:
# This helper creates a new platform instance for workflow integration tests.
def build_platform() -> SkillsAIPlatform:
    """Create a fresh platform instance with shared workflow orchestration enabled."""
    # Line comment: instantiate the full platform composition used by gateway and analytics tests.
    return SkillsAIPlatform()


# Block comment:
# This test verifies the standalone orchestration service tracks queued-to-completed job lifecycle.
def test_workflow_service_runs_registered_job_and_updates_job_record() -> None:
    """Ensure the workflow service executes one registered job and stores its result."""
    # Line comment: create isolated stores and orchestration service for a low-level lifecycle test.
    stores = PlatformStores()
    service = WorkflowOrchestrationService(stores)

    # Block comment:
    # This handler simulates one long-running store update job managed by the workflow service.
    def update_mart_job(payload: dict[str, object], job_context: dict[str, object]) -> dict[str, object]:
        """Persist one mart update and return a compact workflow result payload."""
        # Line comment: update the mart store so the test can assert visible side effects.
        stores.mart[str(payload["metric_key"])] = float(payload["value"])
        return {
            "job_id": str(job_context["job_id"]),
            "metric_key": str(payload["metric_key"]),
            "value": float(payload["value"]),
        }

    service.register_workflow(
        "test.mart_update",
        update_mart_job,
        container="tests",
        description="Update one mart metric for workflow orchestration coverage.",
        store_targets=("mart",),
    )
    # Line comment: submit one background job and then wait for its final terminal state.
    queued_job = service.submit_workflow(
        "test.mart_update",
        {"metric_key": "coverage:all", "value": 0.91},
        trigger="unit-test",
    )
    completed_job = service.wait_for_job(str(queued_job["job_id"]), timeout_seconds=2.0)
    assert completed_job["state"] == "completed"
    assert stores.mart["coverage:all"] == 0.91
    assert completed_job["result"]["metric_key"] == "coverage:all"


# Block comment:
# This test verifies gateway command/query routes expose background workflow submission and polling.
def test_gateway_can_queue_and_query_materialization_workflow() -> None:
    """Ensure analytics materialization can run in background and be queried by job id."""
    # Line comment: create a platform with enough source data for KPI materialization to publish rows.
    platform = build_platform()
    platform.stores.meta["kpi_definitions"] = {
        "skill_coverage": {"multiplier": 1.0, "cohort": "all"},
    }
    platform.stores.time_series.append({"event": "assessment_evidence"})
    # Line comment: queue a background analytics workflow job through the gateway command path.
    queue_response = platform.gateway.handle(
        PlatformRequest(
            method="POST",
            path="/command/analytics/materialize",
            actor_id="manager-1",
            token="manager-1:default",
            payload={"trigger": "integration-test", "wait_for_completion": False},
        )
    )
    job_id = queue_response.body["data"]["materialization_run"]["job"]["job_id"]
    # Line comment: wait for the background workflow to finish before polling its query route.
    platform.analytics.wait_for_workflow_job(str(job_id), timeout_seconds=2.0)
    query_response = platform.gateway.handle(
        PlatformRequest(
            method="GET",
            path="/workflows",
            actor_id="manager-1",
            token="manager-1:default",
            payload={"job_id": job_id},
        )
    )
    workflow_job = query_response.body["data"]["workflow_job"]
    assert workflow_job["job_id"] == job_id
    assert workflow_job["state"] == "completed"
    assert workflow_job["result"]["published_rows"] >= 1
