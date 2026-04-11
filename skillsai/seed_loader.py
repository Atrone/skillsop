"""Seed-data loader for the SkillsAI backend stores."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

try:
    from .platform import SkillsAIPlatform
except ImportError:
    from platform import SkillsAIPlatform

DEFAULT_PROFICIENCY_SCALE = ["L1", "L2", "L3", "L4", "L5"]


# Block comment:
# This helper resolves the seed-data directory from env or repo-relative defaults.
def resolve_seed_data_dir() -> Path:
    """Resolve the directory that contains backend seed-data JSON files."""
    # Line comment: allow operators to override the repo-relative seed-data location.
    configured_dir = os.getenv("SKILLSAI_SEED_DATA_DIR", "").strip()
    if configured_dir:
        return Path(configured_dir).expanduser().resolve()
    # Line comment: default to the repository seed-data folder next to the package.
    return Path(__file__).resolve().parent.parent / "seed-data"


# Block comment:
# This helper loads one JSON seed file into a Python dictionary payload.
def _read_seed_json(seed_data_dir: Path, relative_path: str) -> dict[str, Any]:
    """Read and parse one JSON document from the seed-data tree."""
    # Line comment: build an absolute file path inside the configured seed-data folder.
    target_path = seed_data_dir / relative_path
    # Line comment: parse the JSON document into an in-memory Python structure.
    return json.loads(target_path.read_text(encoding="utf-8"))


# Block comment:
# This helper stores seed-platform metadata used by admin-facing frontend views.
def _load_platform_seed(platform: SkillsAIPlatform, seed_data_dir: Path) -> None:
    """Load gateway-level seed metadata for platform and admin views."""
    # Line comment: read platform index plus sample request documents.
    platform_index = _read_seed_json(seed_data_dir, "platform/index.json")
    request_samples = _read_seed_json(seed_data_dir, "platform/platform-request-samples.json")
    health_response = _read_seed_json(seed_data_dir, "platform/health-response.json")
    # Line comment: persist seed metadata into META for later admin queries.
    platform.stores.meta["seed_platform_index"] = platform_index
    platform.stores.meta["seed_platform_payloads"] = platform_index.get("available_payloads", {})
    platform.stores.meta["seed_platform_request_samples"] = request_samples.get("samples", [])
    platform.stores.meta["seed_platform_health_response"] = health_response


# Block comment:
# This helper hydrates canonical identities and external links from seed-data.
def _load_identity_seed(platform: SkillsAIPlatform, seed_data_dir: Path) -> None:
    """Load identity records and external identity links into cache/audit stores."""
    # Line comment: read canonical identity payloads from the identity seed file.
    identity_seed = _read_seed_json(seed_data_dir, "identity/index.json")
    for record in identity_seed.get("identities", []):
        # Line comment: normalize each record through the identity mapper API.
        platform.identity_mapper.upsert_identity(
            str(record["actor_id"]),
            {
                "tenant_id": record.get("tenant_id", "default-tenant"),
                "roles": list(record.get("roles", ["employee"])),
                "claims": dict(record.get("claims", {})),
            },
        )
    for link in identity_seed.get("external_links", []):
        # Line comment: persist deterministic external-to-canonical identity links.
        platform.identity_mapper.link_identity(
            str(link["external_id"]),
            str(link["employee_id"]),
        )


# Block comment:
# This helper hydrates taxonomy metadata and skill-state read models from seed-data.
def _load_core_seed(platform: SkillsAIPlatform, seed_data_dir: Path) -> None:
    """Load core-intelligence taxonomy and seeded skill-state read models."""
    # Line comment: read the full core-intelligence seed payload.
    core_seed = _read_seed_json(seed_data_dir, "core-intelligence/index.json")
    taxonomy = dict(core_seed.get("taxonomy", {}))
    version = str(taxonomy.get("active_version", "seed"))
    # Line comment: publish the active taxonomy version for frontend read paths.
    platform.core_intelligence.taxonomy.publish_taxonomy_version(
        platform.stores,
        version=version,
        ontology={"skills": list(taxonomy.get("skills", []))},
        job_mappings=dict(taxonomy.get("job_mappings", {})),
        proficiency_scales={"default": list(DEFAULT_PROFICIENCY_SCALE)},
    )
    for employee_id, states in core_seed.get("skill_states", {}).items():
        for seeded_state in states:
            # Line comment: translate each seed record into the graph/mart structures used by reads.
            skill_id = str(seeded_state["skill_id"])
            key = f"{employee_id}:{skill_id}"
            state_payload = {
                "employee_id": str(employee_id),
                "skill_id": skill_id,
                "proficiency": float(seeded_state.get("proficiency", 0.0)),
                "confidence": float(seeded_state.get("confidence", 0.0)),
                "gap": float(seeded_state.get("gap", 0.0)),
                "explanation": "Loaded from seed-data core-intelligence state.",
                "model_version": version,
            }
            platform.stores.put("graph", key, state_payload)
            platform.stores.put(
                "mart",
                key,
                {
                    "proficiency": state_payload["proficiency"],
                    "confidence": state_payload["confidence"],
                    "gap": state_payload["gap"],
                },
            )
            platform.stores.put(
                "meta",
                f"lineage:{key}",
                {"model_version": version, "source": "seed-data"},
            )
    for signal in core_seed.get("evidence_signals", []):
        # Line comment: preserve raw seed evidence history for timeline-style frontend views.
        platform.stores.append(
            "time_series",
            {
                "event": "seed_evidence_signal",
                "employee_id": signal.get("employee_id"),
                "skill_id": signal.get("skill_id"),
                "value": signal.get("value"),
                "source": signal.get("source"),
                "confidence_hint": signal.get("confidence_hint"),
            },
        )


# Block comment:
# This helper loads coaching recommendations and activation metrics from seed-data.
def _load_activation_seed(platform: SkillsAIPlatform, seed_data_dir: Path) -> None:
    """Load activation recommendations, actions, and derived activation metrics."""
    # Line comment: read the activation-services seed payload.
    activation_seed = _read_seed_json(seed_data_dir, "activation/index.json")
    coaching = dict(activation_seed.get("coaching", {}))
    employee_id = str(coaching.get("employee_id", ""))
    if employee_id:
        # Line comment: store the seeded recommendation set for direct coaching reads.
        platform.stores.put(
            "cache",
            f"activation:{employee_id}",
            {
                "employee_id": employee_id,
                "recommendations": list(coaching.get("recommendations", [])),
            },
        )
    for action in activation_seed.get("actions", []):
        # Line comment: mirror seeded activation outcomes into the same mart/time-series stores as runtime events.
        metric_key = str(action.get("metric_key", "activation:unknown:unknown"))
        platform.stores.mart[metric_key] = action.get("value", 0)
        platform.stores.append(
            "time_series",
            {
                "event": "seed_activation_action",
                "action_type": action.get("action_type"),
                "skill_id": action.get("skill_id"),
                "outcome": action.get("outcome"),
                "metric_key": metric_key,
                "value": action.get("value", 0),
            },
        )


# Block comment:
# This helper loads assessment packages and attempt records from seed-data.
def _load_assessment_seed(platform: SkillsAIPlatform, seed_data_dir: Path) -> None:
    """Load seeded assessment packages and attempt read models."""
    # Line comment: read the assessment package index from the seed-data folder.
    assessments_seed = _read_seed_json(seed_data_dir, "assessments/index.json")
    for package in assessments_seed.get("assessment_packages", []):
        # Line comment: normalize seed package fields to the assessment publication definition shape.
        definition = {
            "sections": list(package.get("blueprint", {}).get("sections", [])),
            "duration_min": package.get("blueprint", {}).get("duration_min", 30),
            "items": list(package.get("items", [])),
            "rubric": dict(package.get("rubric", {})),
            "blueprint": dict(package.get("blueprint", {})),
            "version": package.get("version", 1),
        }
        platform.assessments.publish_assessment(str(package["assessment_id"]), definition=definition)
    for attempt in assessments_seed.get("attempts", []):
        # Line comment: store attempts directly in the shape expected by read_attempt and scoring flows.
        platform.stores.attempts[str(attempt["attempt_id"])] = {
            "session": {
                "attempt_id": str(attempt["attempt_id"]),
                "employee_id": str(attempt["employee_id"]),
                "assessment_id": str(attempt["assessment_id"]),
                "status": str(attempt.get("status", "submitted")),
            },
            "responses": dict(attempt.get("responses", {})),
            "scores": dict(attempt.get("scores", {})),
        }


# Block comment:
# This helper loads analytics read models so the frontend can query live backend APIs.
def _load_analytics_seed(platform: SkillsAIPlatform, seed_data_dir: Path) -> None:
    """Load seeded analytics KPI, trend, planning, and run metadata."""
    # Line comment: read analytics snapshots and materialization metadata.
    analytics_seed = _read_seed_json(seed_data_dir, "analytics/index.json")
    read_models = dict(analytics_seed.get("read_models", {}))
    kpi_snapshot = dict(read_models.get("kpi_snapshot", {}))
    if kpi_snapshot:
        # Line comment: publish the current KPI value into MART for analytics queries.
        metric = str(kpi_snapshot.get("metric", "skill_coverage"))
        cohort = str(kpi_snapshot.get("cohort", "all"))
        platform.stores.mart[f"{metric}:{cohort}"] = kpi_snapshot.get("data", {}).get("value", 0.0)
    trend_snapshot = dict(read_models.get("trend_snapshot", {}))
    if trend_snapshot:
        # Line comment: append historical points into the analytics warehouse for trend reads.
        for value in trend_snapshot.get("data", {}).get("series", []):
            platform.stores.append(
                "warehouse",
                {
                    "metric": trend_snapshot.get("metric", "trend.skill_coverage"),
                    "cohort": trend_snapshot.get("cohort", "all"),
                    "value": value,
                    "snapshot_date": analytics_seed.get("seeded_on", "seed"),
                },
            )
    planning_snapshot = dict(read_models.get("planning_snapshot", {}))
    if planning_snapshot:
        # Line comment: store the planning target as the baseline input for planning queries.
        cohort = str(planning_snapshot.get("cohort", "all"))
        target_value = planning_snapshot.get("data", {}).get("target", 1.0)
        platform.stores.mart[f"baseline:{cohort}"] = target_value
    # Line comment: preserve the documented materialization run for admin/governance queries.
    platform.stores.meta["seed_analytics_run"] = analytics_seed.get("materialization_run", {})


# Block comment:
# This function loads the full seed-data tree into the in-memory platform stores.
def load_seed_data(platform: SkillsAIPlatform, seed_data_dir: Path | None = None) -> None:
    """Load all supported seed-data modules into the backend platform."""
    # Line comment: resolve caller override or environment/default seed-data directory.
    effective_seed_dir = seed_data_dir or resolve_seed_data_dir()
    platform.stores.meta["seed_data_dir"] = str(effective_seed_dir)
    if not effective_seed_dir.exists():
        # Line comment: record missing seed-data status so the API can fallback gracefully.
        platform.stores.meta["seed_data_loaded"] = False
        platform.stores.meta["seed_modules"] = []
        return
    # Line comment: load every seed module used by backend and frontend views.
    _load_platform_seed(platform, effective_seed_dir)
    _load_identity_seed(platform, effective_seed_dir)
    _load_core_seed(platform, effective_seed_dir)
    _load_activation_seed(platform, effective_seed_dir)
    _load_assessment_seed(platform, effective_seed_dir)
    _load_analytics_seed(platform, effective_seed_dir)
    platform.stores.meta["seed_data_loaded"] = True
    platform.stores.meta["seed_modules"] = [
        "platform",
        "identity",
        "core-intelligence",
        "activation",
        "assessments",
        "analytics",
    ]
