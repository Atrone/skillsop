"""Comprehensive unit coverage for the SkillsAI backend modules."""

from __future__ import annotations

import json
import importlib
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

sys.modules.pop("skillsai", None)
api_module = importlib.import_module("skillsai.app")
main_module = importlib.import_module("skillsai.main")
seed_loader_module = importlib.import_module("skillsai.seed_loader")
from skillsai.containers.activation_services import ActivationServicesAPI
from skillsai.containers.analytics_longitudinal import (
    AnalyticsLongitudinalContainer,
    AnalyticsService,
    KPIMaterializer,
    SnapshotScheduler,
)
from skillsai.containers.assessments import (
    AssignmentResolver,
    AuthoringUIAPI,
    BlueprintDesigner,
    CalibrationReliability,
    DeliveryUIAPI,
    EvidenceMapper,
    FormRenderer,
    InferenceFeedPublisher,
    ItemAuthoringStudio,
    MetricsUpdater,
    ObjectiveScorer,
    OutcomeEventBuilder,
    ResponseCapture,
    RubricEditor,
    RubricScorer,
    ScoreNormalizer,
    ScoringIntake,
    ScoringPublisher,
    SessionManager,
    SkillSignalTranslator,
    SkillsAIAssessments,
    SkillsAIAssessmentsContainer,
    SubmissionManager,
    VersionPublishWorkflow,
)
from skillsai.containers.core_intelligence import (
    CoreIntelligenceAPI,
    CoreIntelligenceContainer,
    GovernanceService,
    InferenceService,
    TaxonomyService,
)
from skillsai.containers.federation_gateway import (
    AuditHook,
    AuthAdapter,
    CommandOrchestrator,
    FeatureFlagEvaluator,
    FederationGateway,
    FederationGatewayContainer,
    QueryComposer,
    RateLimiter,
    RequestRouter,
    ResponseComposer,
    SessionContextBuilder,
    TenantResolver,
    WebAPIEntry,
)
from skillsai.containers.identity_mapper import IdentityMapperAPI
from skillsai.event_bus import EventBus, PlatformEventBus
from skillsai.models import AssessmentSubmission, EvidenceSignal, KPIQuery, PlatformRequest, RequestContext, SkillState
from skillsai.skills_platform import SkillsAIPlatform
from skillsai.seed_loader import (
    DEFAULT_PROFICIENCY_SCALE,
    SOURCE_KIND_CUSTOMER_RECORDS,
    SourceIntegration,
    SourceIntegrationHubConfig,
    _load_activation_seed,
    _load_analytics_seed,
    _load_assessment_seed,
    _load_core_seed,
    _load_identity_seed,
    _load_platform_seed,
    _read_seed_json,
    load_seed_data,
    read_source_integration_config,
    resolve_seed_data_dir,
)
from skillsai.stores import PlatformStores


# Block comment:
# This helper builds a canonical request context for activation and gateway tests.
def build_request_context(actor_id: str = "emp-1", tenant_id: str = "default-tenant") -> RequestContext:
    """Create a deterministic request context for unit tests."""
    # Line comment: return a minimal but fully populated context object.
    return RequestContext(
        actor_id=actor_id,
        tenant_id=tenant_id,
        roles=["employee"],
        claims={"tenant_hint": tenant_id},
        feature_flags={"assessments_enabled": True},
    )


# Block comment:
# This helper builds a canonical platform request for federation gateway tests.
def build_platform_request(
    path: str = "/analytics",
    method: str = "GET",
    actor_id: str = "emp-1",
    token: str = "emp-1:default",
    payload: dict[str, object] | None = None,
) -> PlatformRequest:
    """Create a deterministic platform request payload for unit tests."""
    # Line comment: normalize omitted payloads to an empty dictionary.
    return PlatformRequest(
        method=method,
        path=path,
        actor_id=actor_id,
        token=token,
        payload=payload or {},
    )


# Block comment:
# This helper builds a canonical assessment submission for scoring flow tests.
def build_submission(
    attempt_id: str = "attempt-1",
    assessment_id: str = "asm-1",
    employee_id: str = "emp-1",
    responses: dict[str, object] | None = None,
) -> AssessmentSubmission:
    """Create a deterministic assessment submission object for unit tests."""
    # Line comment: default to one correct and one incorrect response for score-path coverage.
    return AssessmentSubmission(
        attempt_id=attempt_id,
        assessment_id=assessment_id,
        employee_id=employee_id,
        responses=responses or {"q1": True, "q2": False},
    )


# Block comment:
# This helper writes one JSON file into a temporary seed-data directory tree.
def write_seed_json(seed_data_dir: Path, relative_path: str, payload: dict[str, object]) -> None:
    """Write a JSON document under the provided seed-data directory."""
    # Line comment: create parent directories before persisting the JSON payload.
    target_path = seed_data_dir / relative_path
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(payload), encoding="utf-8")


# Block comment:
# This helper creates a fully populated seed-data tree for seed loader tests.
def build_seed_tree(seed_data_dir: Path) -> None:
    """Create a minimal but complete seed-data directory structure."""
    # Line comment: write the platform seed files consumed by admin and health loaders.
    write_seed_json(
        seed_data_dir,
        "platform/index.json",
        {"available_payloads": {"identity": ["employee_id"], "analytics": ["metric", "cohort"]}},
    )
    write_seed_json(
        seed_data_dir,
        "platform/platform-request-samples.json",
        {"samples": [{"path": "/identity"}, {"path": "/analytics"}]},
    )
    write_seed_json(seed_data_dir, "platform/health-response.json", {"status": "ok", "service": "skillsai-backend"})
    # Line comment: write seed identities and external links.
    write_seed_json(
        seed_data_dir,
        "identity/index.json",
        {
            "identities": [
                {
                    "actor_id": "emp-1",
                    "tenant_id": "default-tenant",
                    "roles": ["employee"],
                    "claims": {"department": "analytics"},
                }
            ],
            "external_links": [{"external_id": "hr-123", "employee_id": "emp-1"}],
        },
    )
    # Line comment: write taxonomy, seeded skill states, and historical evidence signals.
    write_seed_json(
        seed_data_dir,
        "core-intelligence/index.json",
        {
            "taxonomy": {
                "active_version": "v-seed",
                "skills": [{"id": "skill:python"}],
                "job_mappings": {"analyst": ["skill:python"]},
            },
            "skill_states": {
                "emp-1": [
                    {
                        "skill_id": "skill:python",
                        "proficiency": 0.6,
                        "confidence": 0.7,
                        "gap": 0.2,
                    }
                ]
            },
            "evidence_signals": [
                {
                    "employee_id": "emp-1",
                    "skill_id": "skill:python",
                    "value": 0.8,
                    "source": "seed",
                    "confidence_hint": 0.9,
                }
            ],
        },
    )
    # Line comment: write activation coaching recommendations and action metrics.
    write_seed_json(
        seed_data_dir,
        "activation/index.json",
        {
            "coaching": {
                "employee_id": "emp-1",
                "recommendations": [{"type": "coaching", "skill_id": "skill:python", "priority": 0.4}],
            },
            "actions": [
                {
                    "metric_key": "activation:coaching:accepted",
                    "action_type": "coaching",
                    "skill_id": "skill:python",
                    "outcome": "accepted",
                    "value": 1,
                }
            ],
        },
    )
    # Line comment: write one assessment package and one completed attempt.
    write_seed_json(
        seed_data_dir,
        "assessments/index.json",
        {
            "assessment_packages": [
                {
                    "assessment_id": "asm-1",
                    "blueprint": {"sections": [{"name": "Core"}], "duration_min": 45},
                    "items": [{"id": "q1", "skill_id": "skill:python"}],
                    "rubric": {"type": "binary"},
                    "version": 2,
                }
            ],
            "attempts": [
                {
                    "attempt_id": "attempt-1",
                    "employee_id": "emp-1",
                    "assessment_id": "asm-1",
                    "status": "submitted",
                    "responses": {"q1": True},
                    "scores": {"final": 0.8},
                }
            ],
        },
    )
    # Line comment: write analytics read models and documented materialization metadata.
    write_seed_json(
        seed_data_dir,
        "analytics/index.json",
        {
            "seeded_on": "2026-04-10",
            "read_models": {
                "kpi_snapshot": {
                    "metric": "skill_coverage",
                    "cohort": "all",
                    "data": {"value": 0.91},
                },
                "trend_snapshot": {
                    "metric": "trend.skill_coverage",
                    "cohort": "all",
                    "data": {"series": [0.7, 0.8]},
                },
                "planning_snapshot": {
                    "cohort": "all",
                    "data": {"target": 0.95},
                },
            },
            "materialization_run": {"run_id": "seed-run"},
        },
    )


# Block comment:
# This helper creates a representative customer-record payload tree for integration hub tests.
def build_customer_record_tree(customer_records_dir: Path) -> None:
    """Create a minimal but complete customer-record directory structure."""
    # Line comment: write a provider-scoped Workday-style export with identity, skills, coaching, and analytics data.
    write_seed_json(
        customer_records_dir,
        "workday/index.json",
        {
            "tenant_id": "acme-tenant",
            "model_version": "workday-v1",
            "taxonomy": {
                "active_version": "workday-taxonomy",
                "skills": [{"id": "skill:sql"}],
                "job_mappings": {"analyst": ["skill:sql"]},
            },
            "workers": [
                {
                    "worker_id": "wd-100",
                    "employee_id": "emp-100",
                    "roles": ["employee"],
                    "department": "finance",
                    "location": "remote",
                    "skill_states": [
                        {
                            "skill_id": "skill:sql",
                            "proficiency": 0.75,
                            "confidence": 0.8,
                            "gap": 0.05,
                        }
                    ],
                    "recommendations": [
                        {"type": "coaching", "skill_id": "skill:sql", "priority": 0.35}
                    ],
                }
            ],
            "assessment_packages": [
                {
                    "assessment_id": "asm-workday",
                    "version": 2,
                    "blueprint": {"sections": [{"name": "SQL"}], "duration_min": 20},
                    "items": [{"id": "q-workday", "skill_id": "skill:sql"}],
                    "rubric": {"type": "binary"},
                }
            ],
            "attempts": [
                {
                    "attempt_id": "attempt-workday",
                    "employee_id": "emp-100",
                    "assessment_id": "asm-workday",
                    "status": "submitted",
                    "responses": {"q-workday": "answer"},
                    "scores": {"final": 0.92},
                }
            ],
            "analytics": {
                "read_models": {
                    "kpi_snapshot": {
                        "metric": "skill_coverage",
                        "cohort": "finance",
                        "data": {"value": 0.88},
                    },
                    "planning_snapshot": {
                        "cohort": "finance",
                        "data": {"target": 0.95},
                    },
                },
                "materialization_run": {"run_id": "workday-run"},
            },
        },
    )


# Block comment:
# This helper builds Workday API payloads that mirror the new static mock service route tree.
def build_workday_api_payloads(base_url: str) -> dict[str, dict[str, Any]]:
    """Return deterministic mock Workday API responses keyed by request URL."""
    # Line comment: expose the same tenant and endpoint structure as the docker-backed Workday mock service.
    return {
        base_url: {
            "tenant": "acme",
            "resources": [
                {"name": "workers", "path": "/api/v1/acme/workers"},
                {"name": "jobs", "path": "/api/v1/acme/jobs"},
                {"name": "organizations", "path": "/api/v1/acme/organizations"},
                {"name": "locations", "path": "/api/v1/acme/locations"},
            ],
        },
        f"{base_url}/workers": {
            "count": 1,
            "data": [
                {
                    "id": "wid-1001",
                    "descriptor": "Avery Jordan",
                    "employeeId": "1001",
                    "businessTitle": "Senior Analytics Engineer",
                    "supervisoryOrganization": {"id": "org-finance", "descriptor": "Finance Analytics"},
                    "location": {"id": "loc-austin", "descriptor": "Austin Hub"},
                    "links": [
                        {"rel": "self", "href": "/api/v1/acme/workers/wid-1001"},
                        {"rel": "basic", "href": "/api/v1/acme/workers/wid-1001/basic"},
                        {"rel": "talent", "href": "/api/v1/acme/workers/wid-1001/talent"},
                    ],
                }
            ],
        },
        f"{base_url}/workers/wid-1001": {
            "id": "wid-1001",
            "descriptor": "Avery Jordan",
            "employeeId": "1001",
            "personal": {
                "firstName": "Avery",
                "lastName": "Jordan",
                "email": "avery.jordan@example.com",
            },
            "employment": {
                "workerType": "Employee",
                "active": True,
                "businessTitle": "Senior Analytics Engineer",
            },
            "jobProfile": {"id": "job-analytics-engineer", "descriptor": "Analytics Engineer"},
            "organizations": [
                {"id": "org-finance", "descriptor": "Finance Analytics", "type": "Supervisory"}
            ],
            "location": {"id": "loc-austin", "descriptor": "Austin Hub"},
            "manager": {"id": "wid-2001", "descriptor": "Morgan Lee"},
        },
        f"{base_url}/workers/wid-1001/basic": {
            "id": "wid-1001",
            "employeeId": "1001",
            "descriptor": "Avery Jordan",
            "workEmail": "avery.jordan@example.com",
            "businessTitle": "Senior Analytics Engineer",
            "manager": {"id": "wid-2001", "descriptor": "Morgan Lee"},
            "location": {"id": "loc-austin", "descriptor": "Austin Hub"},
        },
        f"{base_url}/workers/wid-1001/talent": {
            "id": "wid-1001",
            "descriptor": "Avery Jordan",
            "skills": [
                {"id": "skill-sql", "descriptor": "SQL", "proficiency": "Advanced"},
                {"id": "skill-python", "descriptor": "Python", "proficiency": "Advanced"},
                {"id": "skill-data-modeling", "descriptor": "Data Modeling", "proficiency": "Intermediate"},
            ],
            "careerInterests": ["Principal Analytics Engineer"],
        },
        f"{base_url}/jobs": {
            "count": 1,
            "data": [
                {
                    "id": "job-analytics-engineer",
                    "descriptor": "Analytics Engineer",
                    "links": [{"rel": "self", "href": "/api/v1/acme/jobs/job-analytics-engineer"}],
                }
            ],
        },
        f"{base_url}/jobs/job-analytics-engineer": {
            "id": "job-analytics-engineer",
            "descriptor": "Analytics Engineer",
            "jobLevel": "P4",
            "skills": ["SQL", "Python", "Data Modeling"],
        },
        f"{base_url}/organizations": {
            "count": 1,
            "data": [
                {
                    "id": "org-finance",
                    "descriptor": "Finance Analytics",
                    "type": "Supervisory",
                    "links": [{"rel": "self", "href": "/api/v1/acme/organizations/org-finance"}],
                }
            ],
        },
        f"{base_url}/organizations/org-finance": {
            "id": "org-finance",
            "descriptor": "Finance Analytics",
            "type": "Supervisory",
            "company": {"name": "Acme Corp"},
            "staffing": {"headcount": 18, "openPositions": 2},
            "location": {"id": "loc-austin", "descriptor": "Austin Hub"},
        },
        f"{base_url}/locations": {
            "count": 1,
            "data": [
                {
                    "id": "loc-austin",
                    "descriptor": "Austin Hub",
                    "links": [{"rel": "self", "href": "/api/v1/acme/locations/loc-austin"}],
                }
            ],
        },
        f"{base_url}/locations/loc-austin": {
            "id": "loc-austin",
            "descriptor": "Austin Hub",
            "timezone": "America/Chicago",
            "address": {"city": "Austin", "country": "US"},
        },
    }


# Block comment:
# This helper simulates a missing seed-data load so API fallback seeding can be exercised.
def mark_seed_data_unloaded(platform: SkillsAIPlatform) -> None:
    """Mark seed loading as unavailable for create_app unit tests."""
    # Line comment: store the same metadata flag that the real loader would set on a missing directory.
    platform.stores.meta["seed_data_loaded"] = False


# Block comment:
# This test verifies API helpers parse CORS origins and seed fallback data correctly.
def test_api_helpers_parse_origins_and_seed_demo_data(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure API helper functions normalize origins and create fallback demo records."""
    # Line comment: trim whitespace and ignore empty CORS origin segments from the environment.
    monkeypatch.setenv("SKILLSAI_CORS_ORIGINS", " http://localhost:3000 , , http://example.com ")
    assert api_module.read_cors_origins() == ["http://localhost:3000", "http://example.com"]
    # Line comment: seed fallback demo data into a fresh platform and keep it idempotent.
    platform = SkillsAIPlatform()
    api_module.seed_demo_data(platform)
    api_module.seed_demo_data(platform)
    assert platform.stores.cache["identity:emp-1"]["tenant_id"] == "default-tenant"
    assert "asm-1" in platform.stores.item_bank


# Block comment:
# This test verifies FastAPI app creation, route behavior, and mapped gateway errors.
def test_create_app_and_http_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure create_app configures fallback data and route error handling."""
    # Line comment: patch seed loading so this test exercises the fallback seeding branch deterministically.
    monkeypatch.setattr(api_module, "load_seed_data", mark_seed_data_unloaded)
    app = api_module.create_app()
    client = TestClient(app)
    # Line comment: verify health route and fallback-seeded platform state.
    health_response = client.get("/api/v1/health")
    assert health_response.status_code == 200
    assert app.state.platform.stores.cache["identity:emp-1"]["tenant_id"] == "default-tenant"
    # Line comment: verify success path adapts the gateway response model correctly.
    app.state.platform.gateway.handle_request = Mock(
        return_value=SimpleNamespace(status_code=201, body={"ok": True}, audit_id="audit-123")
    )
    success_response = client.post(
        "/api/v1/platform/request",
        json={"method": "GET", "path": "/analytics", "actor_id": "emp-1", "token": "emp-1:default", "payload": {}},
    )
    assert success_response.status_code == 200
    assert success_response.json() == {"status_code": 201, "body": {"ok": True}, "audit_id": "audit-123"}
    # Line comment: verify permission and payload exceptions are translated to HTTP errors.
    app.state.platform.gateway.handle_request = Mock(side_effect=PermissionError("denied"))
    forbidden_response = client.post(
        "/api/v1/platform/request",
        json={"method": "GET", "path": "/analytics", "actor_id": "emp-1", "token": "emp-1:default", "payload": {}},
    )
    app.state.platform.gateway.handle_request = Mock(side_effect=ValueError("bad payload"))
    bad_request_response = client.post(
        "/api/v1/platform/request",
        json={"method": "GET", "path": "/analytics", "actor_id": "emp-1", "token": "emp-1:default", "payload": {}},
    )
    assert forbidden_response.status_code == 403
    assert bad_request_response.status_code == 400
    assert "Invalid request payload" in bad_request_response.json()["detail"]


# Block comment:
# This test verifies runtime entrypoint helpers read configuration and call uvicorn.
def test_main_runtime_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure main module reads host/port overrides and launches uvicorn correctly."""
    # Line comment: verify environment override parsing for server configuration.
    monkeypatch.setenv("SKILLSAI_HOST", "127.0.0.1")
    monkeypatch.setenv("SKILLSAI_PORT", "9001")
    assert main_module.read_server_config() == ("127.0.0.1", 9001)
    # Line comment: patch uvicorn runner and verify the startup target arguments.
    uvicorn_run = Mock()
    monkeypatch.setattr(main_module.uvicorn, "run", uvicorn_run)
    main_module.run()
    uvicorn_run.assert_called_once_with(main_module.app, host="127.0.0.1", port=9001, reload=False)


# Block comment:
# This test verifies the platform composition root wires aliases and event subscriptions.
def test_platform_initialization_and_event_subscriptions() -> None:
    """Ensure the platform composes all containers and registers analytics refresh handlers."""
    # Line comment: instantiate the composition root and inspect alias wiring.
    platform = SkillsAIPlatform()
    assert platform.gateway is platform.federation_gateway
    assert platform.bus is platform.event_bus
    assert len(platform.event_bus._subscribers["SkillStateUpdated"]) == 1
    assert len(platform.event_bus._subscribers["AssessmentEvidencePublished"]) == 1
    assert len(platform.event_bus._subscribers["MobilityRecommendationCreated"]) == 1
    # Line comment: publish one subscribed event and verify the analytics scheduler records a run.
    platform.stores.meta["kpi_definitions"] = {"skill_coverage": {"multiplier": 1.0, "cohort": "all"}}
    platform.event_bus.publish("SkillStateUpdated", {"reason": "test"})
    assert platform.stores.meta["run_ledger"][-1]["state"] == "success"


# Block comment:
# This test verifies dictionary-backed and list-backed platform store helpers.
def test_platform_stores_helpers() -> None:
    """Ensure platform store helper methods read, write, append, and validate store types."""
    # Line comment: exercise successful dictionary and list operations first.
    stores = PlatformStores()
    stores.put("cache", "alpha", {"value": 1})
    stores.append("audit", {"event": "created"})
    assert stores.get("cache", "alpha") == {"value": 1}
    assert stores.get("cache", "missing", {"fallback": True}) == {"fallback": True}
    assert stores.list_records("audit") == [{"event": "created"}]
    # Line comment: verify helper methods reject mismatched store types.
    with pytest.raises(TypeError):
        stores.put("audit", "bad", {"value": 2})
    with pytest.raises(TypeError):
        stores.get("audit", "bad")
    with pytest.raises(TypeError):
        stores.append("cache", {"event": "bad"})
    with pytest.raises(TypeError):
        stores.list_records("cache")


# Block comment:
# This test verifies the event bus dispatches subscribers synchronously and keeps its alias.
def test_event_bus_subscribe_publish_and_alias() -> None:
    """Ensure the event bus dispatches handlers and preserves the semantic alias."""
    # Line comment: register the same handler twice to confirm duplicate subscriptions are supported.
    bus = EventBus()
    received: list[dict[str, object]] = []
    handler = received.append
    bus.subscribe("demo", handler)
    bus.subscribe("demo", handler)
    bus.publish("demo", {"value": 1})
    assert received == [{"value": 1}, {"value": 1}]
    assert PlatformEventBus is EventBus


# Block comment:
# This test verifies the identity mapper create, link, read, and context-resolution paths.
def test_identity_mapper_api_methods() -> None:
    """Ensure identity mapper methods persist canonical identity and request context data."""
    # Line comment: create one mapper and exercise its write and read paths.
    stores = PlatformStores()
    api = IdentityMapperAPI(stores=stores)
    record = api.upsert_identity("emp-1", {"tenant_id": "tenant-a", "roles": ["manager"], "department": "ops"})
    linked = api.link_identity("external-1", "emp-1")
    assert record["tenant_id"] == "tenant-a"
    assert linked == {"external_id": "external-1", "employee_id": "emp-1"}
    assert api.read_identity("emp-1")["roles"] == ["manager"]
    # Line comment: resolve context for both an existing identity and a lazily created fallback identity.
    existing_context = api.resolve_context("emp-1", {"analytics_enabled": True})
    fallback_context = api.resolve_context("emp-2", {"analytics_enabled": False})
    assert existing_context.tenant_id == "tenant-a"
    assert fallback_context.actor_id == "emp-2"
    assert stores.cache["identity:emp-2"]["tenant_id"] == "default-tenant"


# Block comment:
# This test verifies taxonomy, governance, inference, and container-level core intelligence adapters.
def test_core_intelligence_services_and_api() -> None:
    """Ensure core intelligence services persist taxonomy, authorize evidence, and infer skill state."""
    # Line comment: publish taxonomy metadata and verify governance audit behavior.
    stores = PlatformStores()
    bus = EventBus()
    taxonomy = TaxonomyService()
    governance = GovernanceService()
    taxonomy.publish_taxonomy_version(
        stores,
        version="v2",
        ontology={"skills": ["skill:python"]},
        job_mappings={"analyst": ["skill:python"]},
        proficiency_scales={"default": DEFAULT_PROFICIENCY_SCALE},
    )
    stores.cache["consent:emp-1:assessment"] = True
    assert governance.authorize_evidence(stores, "emp-1", "assessment") is True
    stores.cache["consent:emp-2:assessment"] = False
    assert governance.authorize_evidence(stores, "emp-2", "assessment") is False
    governance.apply_retention(stores, "90-days")
    # Line comment: ingest one permitted signal and verify all derived stores and events are updated.
    inference = InferenceService(stores, bus, governance)
    received_events: list[dict[str, object]] = []
    bus.subscribe("SkillStateUpdated", received_events.append)
    state = inference.ingest_evidence(
        EvidenceSignal(
            employee_id="emp-1",
            skill_id="skill:python",
            value=1.2,
            source="assessment",
            confidence_hint=0.9,
            metadata={},
        ),
        model_version="v3",
    )
    assert state.proficiency == 0.5
    assert stores.graph["emp-1:skill:python"]["model_version"] == "v3"
    assert received_events[-1]["key"] == "emp-1:skill:python"
    with pytest.raises(PermissionError):
        inference.ingest_evidence(
            EvidenceSignal(
                employee_id="emp-2",
                skill_id="skill:sql",
                value=0.4,
                source="assessment",
                confidence_hint=0.7,
                metadata={},
            )
        )
    # Line comment: exercise the container API snapshot, read, and payload normalization adapters.
    api = CoreIntelligenceAPI(stores, bus)
    stores.graph["emp-1:skill:sql"] = {"skill_id": "skill:sql", "proficiency": 0.25}
    snapshot = api.get_skill_snapshot(stores, "emp-1", "skill:python")
    states = api.read_skill_states("emp-1")
    signal_state = api.ingest_evidence(
        {
            "employee_id": "emp-1",
            "skill_id": "skill:data",
            "value": 0.6,
            "source": "gateway",
            "confidence_hint": 0.5,
            "model_version": "v4",
        }
    )
    passthrough_state = api.ingest_evidence(
        EvidenceSignal(
            employee_id="emp-1",
            skill_id="skill:governance",
            value=0.3,
            source="assessment",
            confidence_hint=0.8,
            metadata={},
        )
    )
    assert snapshot["taxonomy_version"] == "v2"
    assert "skill:sql" in states
    assert signal_state.model_version == "v4"
    assert passthrough_state.model_version == "v1"
    assert isinstance(CoreIntelligenceContainer(stores, bus), CoreIntelligenceAPI)


# Block comment:
# This test verifies activation recommendation derivation, read flow, action flow, and gateway helpers.
def test_activation_services_api_methods() -> None:
    """Ensure activation services derive recommendations, read seeded data, and publish actions."""
    # Line comment: create activation service with both nested and flat graph state for recommendation coverage.
    stores = PlatformStores()
    bus = EventBus()
    api = ActivationServicesAPI(stores=stores, event_bus=bus)
    stores.graph["emp-1"] = {"skills": {"skill:nested": {"gap": 0.4, "confidence": 0.5}}}
    stores.graph["emp-1:skill:flat"] = {"skill_id": "skill:flat", "gap": 0.8, "confidence": 0.9}
    recommendations = api._build_graph_recommendations("emp-1")
    assert [item["skill_id"] for item in recommendations] == ["skill:flat", "skill:nested"]
    # Line comment: prefer seeded recommendations for read flow and audit the result.
    stores.cache["activation:emp-1"] = {
        "employee_id": "emp-1",
        "recommendations": [{"type": "coaching", "skill_id": "skill:seeded", "priority": 0.2}],
    }
    read_result = api.read(build_request_context(), {"employee_id": "emp-1"})
    assert read_result["recommendations"][0]["skill_id"] == "skill:seeded"
    # Line comment: execute action flow and gateway helper adapters, then verify published metrics.
    published_events: list[dict[str, object]] = []
    bus.subscribe("MobilityRecommendationCreated", published_events.append)
    action_result = api.act(build_request_context(), {"action_type": "mobility", "skill_id": "skill:flat", "outcome": "accepted"})
    coaching_result = api.get_coaching_recommendations("emp-1")
    helper_action = api.create_coaching_action("emp-1", "skill:new")
    assert action_result["metric_key"] == "activation:mobility:accepted"
    assert coaching_result["employee_id"] == "emp-1"
    assert helper_action["metric_key"] == "activation:coaching:accepted"
    assert published_events[-1]["metric_key"] == "activation:coaching:accepted"


# Block comment:
# This test verifies analytics query helpers and the public analytics service run path.
def test_analytics_service_methods() -> None:
    """Ensure analytics service executes KPI, trend, planning, and dashboard rendering logic."""
    # Line comment: populate mart and warehouse stores so each analytics engine has deterministic inputs.
    stores = PlatformStores()
    stores.graph["emp-1:skill:python"] = {"proficiency": 0.7}
    stores.mart["skill_coverage:all"] = 0.82
    stores.mart["baseline:all"] = 0.95
    stores.warehouse.extend(
        [
            {"metric": "trend.skill_coverage", "cohort": "all", "value": 0.7},
            {"metric": "trend.skill_coverage", "cohort": "all", "value": 0.8},
        ]
    )
    service = AnalyticsService(stores)
    kpi_query = KPIQuery(metric="skill_coverage", cohort="all", start="2026-01-01", end="2026-12-31")
    trend_query = KPIQuery(metric="trend.skill_coverage", cohort="all", start="2026-01-01", end="2026-12-31")
    planning_query = KPIQuery(metric="plan.capacity", cohort="all", start="2026-01-01", end="2026-12-31")
    # Line comment: exercise the semantic planner, execution dispatcher, and engine helpers directly.
    kpi_plan = service._semantic_query_layer(kpi_query)
    trend_plan = service._semantic_query_layer(trend_query)
    planning_plan = service._semantic_query_layer(planning_query)
    assert kpi_plan["engine"] == "kpi"
    assert trend_plan["engine"] == "trend"
    assert planning_plan["engine"] == "planning"
    assert service._kpi_query_engine(kpi_plan) == {"value": 0.82, "graph_nodes": 1}
    assert service._trend_and_cohort_analyzer(trend_plan) == {"series": [0.7, 0.8], "average": 0.75}
    assert service._workforce_planning_modeler(planning_plan) == {
        "conservative": 0.9025,
        "target": 0.95,
        "aggressive": 1.045,
    }
    assert service._execute_plan(trend_plan)["average"] == 0.75
    assert service._dashboard_renderer(kpi_query, {"value": 0.82})["metric"] == "skill_coverage"
    # Line comment: verify the public run path renders a full dashboard payload.
    run_result = service.run_query(kpi_query)
    assert run_result["data"]["value"] == 0.82


# Block comment:
# This test verifies scheduler, KPI materializer, and analytics container orchestration methods.
def test_analytics_scheduler_materializer_and_container() -> None:
    """Ensure analytics scheduler and materializer pipelines execute and publish warehouse rows."""
    # Line comment: create input definitions and event history used by both scheduler and materializer.
    stores = PlatformStores()
    stores.meta["kpi_definitions"] = {
        "skill_coverage": {"multiplier": 1.0, "cohort": "all"},
        "skill_depth": {"multiplier": 0.5, "cohort": "all"},
    }
    stores.time_series.extend([{"event": "a"}, {"event": "b"}])
    scheduler = SnapshotScheduler(stores)
    assert scheduler._dependency_resolver() == ["load_kpi_definitions", "calculate_metrics", "aggregate", "snapshot", "publish"]
    assert scheduler._backfill_manager(["task-a"]) == {"recomputed_tasks": ["task-a"], "mode": "incremental"}
    run_entry = scheduler._execution_orchestrator(["task-a", "task-b"])
    trigger_entry = scheduler.trigger_refresh()
    assert run_entry["run_id"] == "run-1"
    assert trigger_entry["run_id"] == "run-2"
    # Line comment: exercise KPI materializer helpers and the full materialize pipeline.
    materializer = KPIMaterializer(stores)
    loaded = materializer._kpi_definition_loader()
    calculated = materializer._metric_calculation_engine(loaded)
    aggregated = materializer._aggregation_engine(calculated + [{"metric": "skill_coverage", "cohort": "all", "value": 1.0}])
    snapshots = materializer._snapshot_builder(aggregated)
    published_rows = materializer._dimensional_publisher(snapshots)
    rerun_rows = materializer.materialize()
    assert "skill_coverage:all" in stores.mart
    assert published_rows[0]["snapshot_date"] == "2026-04-09"
    assert len(rerun_rows) == 2
    # Line comment: verify the analytics container wires service components and exposes façade methods.
    container = AnalyticsLongitudinalContainer(stores=stores, event_bus=EventBus())
    container.handle_bus_event({"reason": "refresh"})
    latest_job = container.list_workflow_jobs(limit=1)[0]
    # Line comment: wait for the queued background workflow before asserting downstream store effects.
    container.wait_for_workflow_job(str(latest_job["job_id"]), timeout_seconds=2.0)
    query_result = container.analytics_query({"metric": "skill_coverage", "cohort": "all"})
    materialization_result = container.trigger_materialization("manual-test")
    assert query_result["metric"] == "skill_coverage"
    assert materialization_result["trigger"] == "manual-test"


# Block comment:
# This test verifies assessment authoring and publication component helpers.
def test_assessment_authoring_components() -> None:
    """Ensure authoring components derive drafts, blueprints, items, rubrics, and packages."""
    # Line comment: build one authored assessment definition and persist it through authoring helpers.
    stores = PlatformStores()
    definition = {
        "sections": [{"name": "Section 1"}],
        "duration_min": 25,
        "items": [{"id": "q1", "skill_id": "skill:python"}],
        "rubric": {"type": "binary"},
    }
    AuthoringUIAPI().author(stores, "asm-1", definition)
    blueprint = BlueprintDesigner().design(definition)
    items = ItemAuthoringStudio().create_items(definition)
    rubric = RubricEditor().build_rubric(definition)
    package = VersionPublishWorkflow().publish(stores, "asm-1", blueprint, items, rubric)
    assert stores.meta["assessment:draft:asm-1"] == definition
    assert blueprint["duration_min"] == 25
    assert items == [{"id": "q1", "skill_id": "skill:python"}]
    assert package["version"] == 1


# Block comment:
# This test verifies delivery and submission components persist assessment session state.
def test_assessment_delivery_and_submission_components() -> None:
    """Ensure delivery-related assessment components open sessions, capture responses, and submit attempts."""
    # Line comment: publish one assessment package and flow it through delivery helpers.
    stores = PlatformStores()
    stores.item_bank["asm-1"] = {"assessment_id": "asm-1", "items": [{"id": "q1"}], "rubric": {"type": "binary"}}
    request = DeliveryUIAPI().start("asm-1", "emp-1")
    form = AssignmentResolver().resolve(stores, request)
    session = SessionManager().open_session(stores, form, "emp-1", "attempt-1")
    rendered = FormRenderer().render(form)
    ResponseCapture().capture(stores, "attempt-1", {"q1": True})
    SubmissionManager().submit(stores, build_submission(responses={"q1": True}))
    assert request == {"assessment_id": "asm-1", "employee_id": "emp-1"}
    assert session["attempt_id"] == "attempt-1"
    assert rendered["assessment_id"] == "asm-1"
    assert stores.attempts["attempt-1"]["session"]["status"] == "submitted"


# Block comment:
# This test verifies scoring, evidence mapping, event building, KPI updates, and inference forwarding.
def test_assessment_scoring_and_evidence_components() -> None:
    """Ensure assessment scoring and evidence publishing component helpers produce stable outputs."""
    # Line comment: score one response payload across objective, rubric, reliability, and normalized output paths.
    stores = PlatformStores()
    stores.attempts["attempt-1"] = {"scores": {}, "responses": {}, "session": {"attempt_id": "attempt-1"}}
    payload = ScoringIntake().intake(build_submission(responses={"q1": True, "q2": 4}))
    objective_score = ObjectiveScorer().score(payload)
    rubric_score = RubricScorer().score(payload)
    reliability = CalibrationReliability().calibrate(objective_score, rubric_score)
    final_score = ScoreNormalizer().normalize(objective_score, rubric_score, reliability)
    ScoringPublisher().publish(stores, "attempt-1", final_score)
    assert objective_score == 0.5
    assert rubric_score == 0.5
    assert reliability == 1.0
    assert stores.attempts["attempt-1"]["scores"]["final"] == 0.5
    # Line comment: convert final score into mapped evidence, durable events, KPI updates, and core outputs.
    mapped = EvidenceMapper().map("asm-1", final_score)
    signals = SkillSignalTranslator().translate("emp-1", mapped)
    events = OutcomeEventBuilder().build("attempt-1", signals)
    MetricsUpdater().update(stores, events)
    core_api = Mock()
    core_api.ingest_evidence = Mock(
        return_value=SkillState(
            employee_id="emp-1",
            skill_id="skill:asm-1",
            proficiency=0.5,
            confidence=0.8,
            gap=0.3,
            explanation="seeded",
            model_version="v1",
        )
    )
    outputs = InferenceFeedPublisher().publish(core_api, signals)
    assert signals[0].skill_id == "skill:asm-1"
    assert events[0]["event"] == "assessment_evidence"
    assert stores.mart["assessment_evidence_events"] == 1
    assert outputs[0].employee_id == "emp-1"


# Block comment:
# This test verifies the assessment façade implements publish, submit, and evidence publication flows.
def test_skills_ai_assessments_facade_methods() -> None:
    """Ensure the assessment façade coordinates authoring, scoring, and evidence publishing end to end."""
    # Line comment: compose the façade with real infrastructure and publish one assessment package.
    stores = PlatformStores()
    bus = EventBus()
    core_api = CoreIntelligenceContainer(stores, bus)
    facade = SkillsAIAssessments(stores=stores, bus=bus)
    package = facade.publish_assessment(
        "asm-1",
        {
            "sections": [{"name": "Foundations"}],
            "items": [{"id": "q1", "skill_id": "skill:asm-1"}],
            "rubric": {"type": "binary"},
        },
    )
    submission = build_submission(responses={"q1": True})
    final_score = facade.submit_assessment(submission)
    outputs = facade.publish_evidence(core_api, submission)
    assert package["assessment_id"] == "asm-1"
    assert final_score == 0.3
    assert outputs[0].skill_id == "skill:asm-1"
    assert any(event["event"] == "assessment_evidence" for event in stores.time_series)


# Block comment:
# This test verifies the assessment container façade methods and payload normalization logic.
def test_assessments_container_methods() -> None:
    """Ensure the assessment container supports publish, read, and submit command paths."""
    # Line comment: compose the container with a real core API so returned states remain dataclasses.
    stores = PlatformStores()
    bus = EventBus()
    core_api = CoreIntelligenceContainer(stores, bus)
    container = SkillsAIAssessmentsContainer(stores=stores, core_api=core_api, event_bus=bus)
    package_from_definition = container.publish_assessment(
        "asm-1",
        definition={
            "sections": [{"name": "Definition"}],
            "items": [{"id": "q1", "skill_id": "skill:asm-1"}],
            "rubric": {"type": "binary"},
        },
    )
    package_from_expanded = container.publish_assessment(
        "asm-2",
        blueprint={"overview": {"title": "Expanded"}},
        items={"q2": {"skill_id": "skill:asm-2"}},
        rubric={"type": "objective"},
        version="v2",
    )
    submit_result = container.submit_assessment(
        {
            "attempt_id": "attempt-1",
            "assessment_id": "asm-1",
            "employee_id": "emp-1",
            "responses": {"q1": True},
        }
    )
    assert package_from_definition["assessment_id"] == "asm-1"
    assert package_from_expanded["assessment_id"] == "asm-2"
    assert container.read_package("asm-1")["assessment_id"] == "asm-1"
    assert container.read_attempt("attempt-1")["session"]["attempt_id"] == "attempt-1"
    assert submit_result["states"][0]["skill_id"] == "skill:asm-1"


# Block comment:
# This test verifies gateway helper components for request acceptance, auth, tenant, flags, and rate limiting.
def test_gateway_helper_components(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure gateway helper components normalize requests, claims, feature flags, and rate limits."""
    # Line comment: exercise request acceptance, authentication, tenant resolution, and session context building.
    stores = PlatformStores()
    stores.cache["id-link:hris:1001"] = "emp-1"
    stores.cache["identity:emp-1"] = {"actor_id": "emp-1", "tenant_id": "tenant-a", "roles": ["employee"]}
    request = build_platform_request()
    assert WebAPIEntry().accept(request) is request
    assert AuthAdapter().authenticate("emp-1:tenant-a") == {"sub": "emp-1", "tenant_hint": "tenant-a"}
    assert AuthAdapter(stores).authenticate("workday:1001:tenant-a", "unknown") == {
        "sub": "emp-1",
        "actor_id": "emp-1",
        "tenant_hint": "tenant-a",
        "roles": ["employee"],
        "auth_provider": "workday",
        "external_subject": "1001",
    }
    with pytest.raises(PermissionError):
        AuthAdapter().authenticate("")
    assert TenantResolver().resolve({"tenant_hint": "tenant-a"}) == "tenant-a"
    context = SessionContextBuilder().build("emp-1", "tenant-a", {"sub": "emp-1"}, {"analytics_enabled": True})
    assert context.roles == ["user"]
    stores.cache["flags:tenant-a"] = {"analytics_enabled": False, "beta": True}
    assert FeatureFlagEvaluator(stores).evaluate("tenant-a") == {
        "assessments_enabled": True,
        "analytics_enabled": False,
        "beta": True,
    }
    # Line comment: verify rate-limit helper methods, legacy counter support, window reset, and hard limits.
    rate_limiter = RateLimiter(stores, max_requests=2)
    monkeypatch.setenv("SKILLSAI_RATE_LIMIT_MAX_REQUESTS", "2")
    monkeypatch.setenv("SKILLSAI_RATE_LIMIT_WINDOW_SECONDS", "10")
    monkeypatch.setattr("skillsai.containers.federation_gateway.time.time", Mock(return_value=100))
    assert rate_limiter._resolve_request_budget() == 2
    assert rate_limiter._resolve_window_seconds() == 10
    stores.cache["rate:emp-1"] = 1
    rate_limiter.throttle("emp-1")
    with pytest.raises(PermissionError):
        rate_limiter.throttle("emp-1")
    monkeypatch.setattr("skillsai.containers.federation_gateway.time.time", Mock(return_value=120))
    rate_limiter.throttle("emp-1")
    monkeypatch.setenv("SKILLSAI_RATE_LIMIT_MAX_REQUESTS", "0")
    rate_limiter.throttle("emp-2")


# Block comment:
# This test verifies gateway query composition, command orchestration, routing, and response composition.
def test_gateway_query_command_router_and_response_components() -> None:
    """Ensure gateway helper components route each query and command path correctly."""
    # Line comment: prepare stubbed downstream APIs and shared stores for all query-path branches.
    stores = PlatformStores()
    stores.audit.extend([{"id": 1}, {"id": 2}])
    stores.time_series.append({"event": "seed"})
    stores.cache["active_taxonomy_version"] = "v1"
    stores.cache["identity:emp-1"] = {"actor_id": "emp-1"}
    stores.meta["seed_data_dir"] = "seed-data"
    stores.meta["seed_modules"] = ["identity"]
    stores.meta["seed_platform_payloads"] = {"identity": ["employee_id"]}
    stores.meta["seed_platform_request_samples"] = [{"path": "/identity"}]
    stores.item_bank["asm-1"] = {"assessment_id": "asm-1"}
    identity_mapper = SimpleNamespace(read_identity=Mock(return_value={"actor_id": "emp-1"}), link_identity=Mock(return_value={"ok": True}))
    core_intelligence = SimpleNamespace(
        read_skill_states=Mock(return_value={"skill:python": {"proficiency": 0.7}}),
        ingest_evidence=Mock(
            return_value=SkillState(
                employee_id="emp-1",
                skill_id="skill:python",
                proficiency=0.7,
                confidence=0.8,
                gap=0.1,
                explanation="ok",
                model_version="v1",
            )
        ),
    )
    activation_services = SimpleNamespace(
        get_coaching_recommendations=Mock(return_value={"recommendations": [{"skill_id": "skill:python"}]}),
        create_coaching_action=Mock(return_value={"status": "recorded"}),
    )
    assessments = SimpleNamespace(
        read_package=Mock(return_value={"assessment_id": "asm-1"}),
        read_attempt=Mock(return_value={"session": {"attempt_id": "attempt-1"}}),
        submit_assessment=Mock(return_value={"score": 1.0}),
    )
    analytics = SimpleNamespace(
        analytics_query=Mock(return_value={"metric": "skill_coverage"}),
        trigger_materialization=Mock(return_value={"trigger": "manual"}),
    )
    query = QueryComposer()
    command = CommandOrchestrator()
    # Line comment: cover every query branch including governance, admin, and unknown routes.
    assert query.execute(stores, "/identity", {"employee_id": "emp-1"}, identity_mapper, core_intelligence, activation_services, assessments, analytics) == {
        "identity": {"actor_id": "emp-1"}
    }
    assert "skills" in query.execute(stores, "/skills", {"employee_id": "emp-1"}, identity_mapper, core_intelligence, activation_services, assessments, analytics)
    assert "coaching" in query.execute(stores, "/coaching", {"employee_id": "emp-1"}, identity_mapper, core_intelligence, activation_services, assessments, analytics)
    assert "mobility" in query.execute(stores, "/mobility", {"employee_id": "emp-1"}, identity_mapper, core_intelligence, activation_services, assessments, analytics)
    assessment_result = query.execute(
        stores,
        "/assessments",
        {"assessment_id": "asm-1", "attempt_id": "attempt-1"},
        identity_mapper,
        core_intelligence,
        activation_services,
        assessments,
        analytics,
    )
    assert assessment_result["assessment"]["assessment_id"] == "asm-1"
    assert query.execute(stores, "/assessments", {}, identity_mapper, core_intelligence, activation_services, assessments, analytics)["message"] == "No assessment identifier provided."
    assert "analytics" in query.execute(stores, "/analytics", {}, identity_mapper, core_intelligence, activation_services, assessments, analytics)
    assert "governance" in query.execute(stores, "/governance", {}, identity_mapper, core_intelligence, activation_services, assessments, analytics)
    assert "admin" in query.execute(stores, "/admin", {}, identity_mapper, core_intelligence, activation_services, assessments, analytics)
    assert query.execute(stores, "/unknown", {}, identity_mapper, core_intelligence, activation_services, assessments, analytics)["message"] == "No query route matched."
    # Line comment: cover every command branch and the request router command/query split.
    assert "identity_linked" in command.execute("/command/identity/link", {"external_id": "x", "employee_id": "emp-1"}, identity_mapper, core_intelligence, activation_services, assessments, analytics)
    assert "skill_state" in command.execute("/command/core/infer", {"employee_id": "emp-1", "skill_id": "skill:python", "value": 0.7}, identity_mapper, core_intelligence, activation_services, assessments, analytics)
    assert "coaching_action" in command.execute("/command/activation/coaching", {"employee_id": "emp-1", "goal_skill": "skill:python"}, identity_mapper, core_intelligence, activation_services, assessments, analytics)
    assert "assessment_result" in command.execute("/command/assessments/submit", {"attempt_id": "attempt-1"}, identity_mapper, core_intelligence, activation_services, assessments, analytics)
    assert "materialization_run" in command.execute("/command/analytics/materialize", {}, identity_mapper, core_intelligence, activation_services, assessments, analytics)
    assert command.execute("/command/unknown", {}, identity_mapper, core_intelligence, activation_services, assessments, analytics)["message"] == "No command route matched."
    router = RequestRouter(query=query, command=command)
    assert "message" in router.route(build_platform_request(path="/unknown"), stores, identity_mapper, core_intelligence, activation_services, assessments, analytics)
    assert "identity_linked" in router.route(
        build_platform_request(path="/command/identity/link", method="POST", payload={"external_id": "x", "employee_id": "emp-1"}),
        stores,
        identity_mapper,
        core_intelligence,
        activation_services,
        assessments,
        analytics,
    )
    assert ResponseComposer().compose({"ok": True}, status_code=200) == {"status": "ok", "data": {"ok": True}}
    assert ResponseComposer().compose({"ok": False}, status_code=500) == {"status": "error", "data": {"ok": False}}


# Block comment:
# This test verifies query and command components enforce user scope when request context is provided.
def test_gateway_query_and_command_enforce_user_scope() -> None:
    """Ensure employee context defaults to self and blocks unauthorized cross-user access."""
    # Line comment: prepare shared stores and component stubs for context-aware authorization checks.
    stores = PlatformStores()
    stores.cache["identity:emp-1"] = {"actor_id": "emp-1", "roles": ["employee"]}
    stores.cache["identity:emp-2"] = {"actor_id": "emp-2", "roles": ["employee"]}
    stores.cache["identity:manager-1"] = {"actor_id": "manager-1", "roles": ["manager"]}
    identity_mapper = SimpleNamespace(
        read_identity=Mock(side_effect=lambda employee_id: {"actor_id": employee_id}),
        link_identity=Mock(return_value={"external_id": "workday:1001", "employee_id": "emp-2"}),
    )
    core_intelligence = SimpleNamespace(
        read_skill_states=Mock(return_value={}),
        ingest_evidence=Mock(
            return_value=SkillState(
                employee_id="emp-1",
                skill_id="skill:python",
                proficiency=0.7,
                confidence=0.8,
                gap=0.1,
                explanation="ok",
                model_version="v1",
            )
        ),
    )
    activation_services = SimpleNamespace(
        get_coaching_recommendations=Mock(return_value={"recommendations": []}),
        create_coaching_action=Mock(return_value={"status": "recorded"}),
    )
    assessments = SimpleNamespace(
        read_package=Mock(return_value={"assessment_id": "asm-1"}),
        read_attempt=Mock(return_value={"session": {"attempt_id": "attempt-1", "employee_id": "emp-2"}}),
        submit_assessment=Mock(return_value={"score": 1.0}),
    )
    analytics = SimpleNamespace(
        analytics_query=Mock(return_value={"metric": "skill_coverage"}),
        trigger_materialization=Mock(return_value={"trigger": "manual"}),
    )
    query = QueryComposer()
    command = CommandOrchestrator()
    employee_context = RequestContext(
        actor_id="emp-1",
        tenant_id="default-tenant",
        roles=["employee"],
        claims={},
        feature_flags={},
    )
    manager_context = RequestContext(
        actor_id="manager-1",
        tenant_id="default-tenant",
        roles=["manager"],
        claims={},
        feature_flags={},
    )
    # Line comment: verify self-scoped reads default to context actor and reject unauthorized cross-user reads.
    assert query.execute(
        stores,
        "/identity",
        {},
        identity_mapper,
        core_intelligence,
        activation_services,
        assessments,
        analytics,
        context=employee_context,
    ) == {"identity": {"actor_id": "emp-1"}}
    with pytest.raises(PermissionError):
        query.execute(
            stores,
            "/identity",
            {"employee_id": "emp-2"},
            identity_mapper,
            core_intelligence,
            activation_services,
            assessments,
            analytics,
            context=employee_context,
        )
    assert query.execute(
        stores,
        "/identity",
        {"employee_id": "emp-2"},
        identity_mapper,
        core_intelligence,
        activation_services,
        assessments,
        analytics,
        context=manager_context,
    ) == {"identity": {"actor_id": "emp-2"}}
    # Line comment: verify self-scoped commands inject employee_id from context and enforce mutation authorization.
    command.execute(
        "/command/core/infer",
        {"skill_id": "skill:python", "value": 0.7},
        identity_mapper,
        core_intelligence,
        activation_services,
        assessments,
        analytics,
        context=employee_context,
    )
    assert core_intelligence.ingest_evidence.call_args.args[0]["employee_id"] == "emp-1"
    with pytest.raises(PermissionError):
        command.execute(
            "/command/core/infer",
            {"employee_id": "emp-2", "skill_id": "skill:python", "value": 0.7},
            identity_mapper,
            core_intelligence,
            activation_services,
            assessments,
            analytics,
            context=employee_context,
        )
    command.execute(
        "/command/identity/link",
        {"external_id": "workday:1001", "employee_id": "emp-2"},
        identity_mapper,
        core_intelligence,
        activation_services,
        assessments,
        analytics,
        context=manager_context,
    )
    with pytest.raises(PermissionError):
        command.execute(
            "/command/identity/link",
            {"external_id": "workday:1001", "employee_id": "emp-2"},
            identity_mapper,
            core_intelligence,
            activation_services,
            assessments,
            analytics,
            context=employee_context,
        )


# Block comment:
# This test verifies audit writing, end-to-end gateway handling, and the container delegation wrapper.
def test_gateway_audit_handle_and_container(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure the federation gateway writes audit records and container delegates to the gateway implementation."""
    # Line comment: patch uuid generation so audit ids are deterministic for the assertions.
    stores = PlatformStores()
    monkeypatch.setattr(
        "skillsai.containers.federation_gateway.uuid4",
        Mock(return_value=SimpleNamespace(hex="abcdef1234567890")),
    )
    audit_id = AuditHook(stores).write("emp-1", "/analytics", {"status": "ok"})
    assert audit_id == "audit-abcdef123456"
    # Line comment: compose a real gateway over mocked container APIs and verify the full pipeline.
    identity_mapper = SimpleNamespace(
        read_identity=Mock(return_value={"actor_id": "emp-1"}),
        link_identity=Mock(return_value={"ok": True}),
        resolve_context=Mock(
            return_value=RequestContext(
                actor_id="emp-1",
                tenant_id="default-tenant",
                roles=["employee"],
                claims={},
                feature_flags={"analytics_enabled": True, "assessments_enabled": True},
            )
        ),
    )
    core_intelligence = SimpleNamespace(
        read_skill_states=Mock(return_value={"skill:python": {"proficiency": 0.7}}),
        ingest_evidence=Mock(
            return_value=SkillState(
                employee_id="emp-1",
                skill_id="skill:python",
                proficiency=0.7,
                confidence=0.8,
                gap=0.1,
                explanation="ok",
                model_version="v1",
            )
        ),
    )
    activation_services = SimpleNamespace(
        get_coaching_recommendations=Mock(return_value={"recommendations": []}),
        create_coaching_action=Mock(return_value={"status": "recorded"}),
    )
    assessments = SimpleNamespace(
        read_package=Mock(return_value={"assessment_id": "asm-1"}),
        read_attempt=Mock(return_value={"session": {"attempt_id": "attempt-1"}}),
        submit_assessment=Mock(return_value={"score": 1.0}),
    )
    analytics = SimpleNamespace(
        analytics_query=Mock(return_value={"metric": "skill_coverage", "data": {"value": 0.8}}),
        trigger_materialization=Mock(return_value={"trigger": "manual"}),
    )
    gateway = FederationGateway(
        stores=stores,
        identity_mapper=identity_mapper,
        core_intelligence=core_intelligence,
        activation_services=activation_services,
        assessments=assessments,
        analytics=analytics,
    )
    response = gateway.handle(
        build_platform_request(
            path="/analytics",
            payload={"metric": "skill_coverage", "cohort": "all"},
        )
    )
    assert response.status_code == 200
    assert response.body["data"]["analytics"]["metric"] == "skill_coverage"
    assert stores.audit[-1]["event_type"] == "GatewayResponse"
    container = FederationGatewayContainer(
        identity_mapper_api=identity_mapper,
        core_intelligence_api=core_intelligence,
        activation_services_api=activation_services,
        assessments_api=assessments,
        analytics_api=analytics,
        stores=stores,
    )
    assert container.handle_request(build_platform_request(path="/unknown")).status_code == 200
    assert container.handle(build_platform_request(path="/unknown")).status_code == 200


# Block comment:
# This test verifies seed directory resolution and raw seed JSON parsing.
def test_seed_loader_directory_resolution_and_json_reading(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure the seed loader resolves explicit directories and parses JSON payloads."""
    # Line comment: prefer explicit environment configuration when it is provided.
    configured_dir = tmp_path / "configured-seeds"
    configured_dir.mkdir()
    monkeypatch.setenv("SKILLSAI_SEED_DATA_DIR", str(configured_dir))
    assert resolve_seed_data_dir() == configured_dir.resolve()
    # Line comment: verify JSON payload parsing from the configured seed tree.
    write_seed_json(configured_dir, "platform/index.json", {"available_payloads": {"identity": ["employee_id"]}})
    assert _read_seed_json(configured_dir, "platform/index.json") == {"available_payloads": {"identity": ["employee_id"]}}


# Block comment:
# This test verifies each seed loader helper populates the expected stores and metadata.
def test_seed_loader_component_helpers(tmp_path: Path) -> None:
    """Ensure each seed loader helper hydrates the expected backend store structures."""
    # Line comment: create a complete temporary seed-data tree and a fresh platform for helper-level loading.
    seed_data_dir = tmp_path / "seed-data"
    build_seed_tree(seed_data_dir)
    platform = SkillsAIPlatform()
    _load_platform_seed(platform, seed_data_dir)
    _load_identity_seed(platform, seed_data_dir)
    _load_core_seed(platform, seed_data_dir)
    _load_activation_seed(platform, seed_data_dir)
    _load_assessment_seed(platform, seed_data_dir)
    _load_analytics_seed(platform, seed_data_dir)
    assert platform.stores.meta["seed_platform_index"]["available_payloads"]["identity"] == ["employee_id"]
    assert platform.stores.cache["identity:emp-1"]["claims"]["claims"]["department"] == "analytics"
    assert platform.stores.graph["emp-1:skill:python"]["model_version"] == "v-seed"
    assert platform.stores.cache["activation:emp-1"]["recommendations"][0]["skill_id"] == "skill:python"
    assert platform.stores.item_bank["asm-1"]["version"] == 1
    assert platform.stores.attempts["attempt-1"]["scores"]["final"] == 0.8
    assert platform.stores.mart["skill_coverage:all"] == 0.91
    assert platform.stores.meta["seed_analytics_run"]["run_id"] == "seed-run"


# Block comment:
# This test verifies full seed loading behavior for both missing and present seed-data directories.
def test_load_seed_data_handles_missing_and_existing_directories(tmp_path: Path) -> None:
    """Ensure load_seed_data records status when seed data is missing and hydrates stores when present."""
    # Line comment: verify graceful fallback metadata when the seed directory is absent.
    missing_platform = SkillsAIPlatform()
    missing_dir = tmp_path / "missing-seed-data"
    load_seed_data(missing_platform, missing_dir)
    assert missing_platform.stores.meta["seed_data_loaded"] is False
    assert missing_platform.stores.meta["seed_modules"] == []
    # Line comment: verify the full module load summary and persisted seed metadata when files exist.
    loaded_platform = SkillsAIPlatform()
    loaded_dir = tmp_path / "seed-data"
    build_seed_tree(loaded_dir)
    load_seed_data(loaded_platform, loaded_dir)
    assert loaded_platform.stores.meta["seed_data_loaded"] is True
    assert loaded_platform.stores.meta["seed_modules"] == [
        "platform",
        "identity",
        "core-intelligence",
        "activation",
        "assessments",
        "analytics",
    ]


# Block comment:
# This test verifies the source integration hub can read JSON configuration entries.
def test_read_source_integration_config_reads_seed_and_customer_sources(tmp_path: Path) -> None:
    """Ensure the source integration config parser preserves ordered seed and customer source settings."""
    # Line comment: write a config file that mixes disabled seed data with an enabled Workday customer source.
    config_path = tmp_path / "source-config.json"
    config_path.write_text(
        json.dumps(
            {
                "sources": [
                    {"name": "seed-data", "kind": "seed_data", "path": "seed-data", "enabled": False},
                    {
                        "name": "workday",
                        "kind": "customer_records",
                        "provider": "workday",
                        "path": "customer-records",
                        "enabled": True,
                        "options": {"mode": "snapshot"},
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    config = read_source_integration_config(config_path)
    assert [source.name for source in config.sources] == ["seed-data", "workday"]
    assert config.sources[0].enabled is False
    assert config.sources[1].kind == SOURCE_KIND_CUSTOMER_RECORDS
    assert config.sources[1].path == (tmp_path / "customer-records").resolve()
    assert config.sources[1].options["mode"] == "snapshot"


# Block comment:
# This test verifies the source integration hub can load Workday customer data through the mock API.
def test_load_seed_data_can_load_customer_record_sources(tmp_path: Path) -> None:
    """Ensure the compatibility loader hydrates stores from Workday API payloads and container computations."""
    # Line comment: provide deterministic mock responses for each Workday API endpoint the loader fetches.
    base_url = "http://mock-workday/api/v1/acme"
    workday_payloads = build_workday_api_payloads(base_url)

    # Block comment:
    # This helper replaces remote HTTP fetches with in-memory Workday mock payloads for the test.
    def mock_fetch_remote_json(url: str) -> dict[str, Any]:
        """Return one copied Workday API payload for the requested URL."""
        # Line comment: deep-copy payloads so the loader cannot mutate shared test fixtures between calls.
        return json.loads(json.dumps(workday_payloads[url]))

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(seed_loader_module, "_fetch_remote_json", mock_fetch_remote_json)
    platform = SkillsAIPlatform()
    try:
        load_seed_data(
            platform,
            source_config=SourceIntegrationHubConfig(
                sources=(
                    SourceIntegration(
                        name="workday",
                        kind=SOURCE_KIND_CUSTOMER_RECORDS,
                        path=(tmp_path / "customer-records").resolve(),
                        provider="workday",
                        options={"base_url": base_url},
                    ),
                )
            ),
        )
    finally:
        # Line comment: release the manual monkeypatch even when assertions fail.
        monkeypatch.undo()
    assert platform.stores.meta["source_data_loaded"] is True
    assert platform.stores.meta["seed_data_loaded"] is False
    assert "customer-records" in platform.stores.meta["source_modules"]
    assert "core-intelligence" in platform.stores.meta["source_modules"]
    assert "activation" in platform.stores.meta["source_modules"]
    assert "analytics" in platform.stores.meta["source_modules"]
    assert platform.stores.cache["identity:emp-1001"]["tenant_id"] == "acme-tenant"
    assert platform.stores.cache["identity:emp-1001"]["claims"]["claims"]["department"] == "Finance Analytics"
    assert platform.stores.cache["id-link:workday:1001"] == "emp-1001"
    assert platform.stores.graph["emp-1001:skill:sql"]["model_version"] == "workday-api-v1"
    assert platform.stores.mart["activation:coaching:accepted"] == 1
    assert platform.stores.warehouse
    assert platform.stores.meta["analytics_run:workday"]["run_id"].startswith("run-")
