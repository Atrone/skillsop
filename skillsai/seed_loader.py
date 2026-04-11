"""Source integration hub for loading seed data and customer record data."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from .skills_platform import SkillsAIPlatform
except ImportError:
    from skills_platform import SkillsAIPlatform

DEFAULT_PROFICIENCY_SCALE = ["L1", "L2", "L3", "L4", "L5"]
SOURCE_KIND_SEED_DATA = "seed_data"
SOURCE_KIND_CUSTOMER_RECORDS = "customer_records"
DEFAULT_SEED_MODULES = [
    "platform",
    "identity",
    "core-intelligence",
    "activation",
    "assessments",
    "analytics",
]


@dataclass(frozen=True)
class SourceIntegration:
    """Configuration for one source integration load step."""

    name: str
    kind: str
    path: Path
    provider: str
    enabled: bool = True
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SourceIntegrationHubConfig:
    """Configuration wrapper for the source integration hub."""

    sources: tuple[SourceIntegration, ...]


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
# This helper resolves the customer-records directory from env or repo-relative defaults.
def resolve_customer_records_dir() -> Path:
    """Resolve the directory that contains customer record JSON files."""
    # Line comment: allow operators to override the repo-relative customer-records location.
    configured_dir = os.getenv("SKILLSAI_CUSTOMER_RECORDS_DIR", "").strip()
    if configured_dir:
        return Path(configured_dir).expanduser().resolve()
    # Line comment: default to the repository customer-records folder next to the package.
    return Path(__file__).resolve().parent.parent / "customer-records"


# Block comment:
# This helper resolves the optional JSON configuration path for source integrations.
def resolve_source_config_path() -> Path | None:
    """Resolve the optional source integration config JSON path."""
    # Line comment: return None when no explicit integration config was provided.
    configured_path = os.getenv("SKILLSAI_SOURCE_CONFIG_PATH", "").strip()
    if not configured_path:
        return None
    # Line comment: normalize the configured path for later file reads.
    return Path(configured_path).expanduser().resolve()


# Block comment:
# This helper normalizes incoming config aliases into supported source kinds.
def _normalize_source_kind(raw_kind: str) -> str:
    """Normalize one source kind or alias into a canonical identifier."""
    # Line comment: compare lower-cased aliases so config is forgiving.
    normalized_kind = raw_kind.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized_kind in {SOURCE_KIND_SEED_DATA, "seed", "seeddata"}:
        return SOURCE_KIND_SEED_DATA
    if normalized_kind in {SOURCE_KIND_CUSTOMER_RECORDS, "customer", "customer_records", "workday", "hris"}:
        return SOURCE_KIND_CUSTOMER_RECORDS
    # Line comment: preserve unknown values so the hub can report them cleanly.
    return normalized_kind


# Block comment:
# This helper normalizes flexible boolean config values from strings or scalars.
def _read_enabled_flag(raw_value: Any) -> bool:
    """Normalize one integration enabled flag to a boolean value."""
    # Line comment: parse common string booleans before falling back to truthiness.
    if isinstance(raw_value, str):
        return raw_value.strip().lower() not in {"0", "false", "no", "off", ""}
    # Line comment: use Python truthiness for non-string config values.
    return bool(raw_value)


# Block comment:
# This helper resolves configured source paths relative to the config file when needed.
def _resolve_source_path(raw_path: str | None, base_dir: Path, kind: str) -> Path:
    """Resolve one source path from config or default directories."""
    # Line comment: fallback to default repo-relative roots when the config omits a path.
    if not raw_path:
        return resolve_seed_data_dir() if kind == SOURCE_KIND_SEED_DATA else resolve_customer_records_dir()
    candidate_path = Path(raw_path).expanduser()
    if not candidate_path.is_absolute():
        candidate_path = (base_dir / candidate_path).resolve()
    # Line comment: return a normalized absolute path for downstream loaders.
    return candidate_path.resolve()


# Block comment:
# This helper builds one typed integration object from JSON configuration.
def _build_source_integration(raw_source: dict[str, Any], base_dir: Path) -> SourceIntegration:
    """Build one source integration definition from a JSON object."""
    # Line comment: normalize source kind first so path/provider defaults are consistent.
    kind = _normalize_source_kind(str(raw_source.get("kind", raw_source.get("type", SOURCE_KIND_SEED_DATA))))
    provider = str(raw_source.get("provider", "seed" if kind == SOURCE_KIND_SEED_DATA else "workday"))
    name = str(raw_source.get("name", provider if kind == SOURCE_KIND_CUSTOMER_RECORDS else "seed-data"))
    path = _resolve_source_path(raw_source.get("path"), base_dir, kind)
    # Line comment: preserve source options for provider-specific behavior extensions.
    return SourceIntegration(
        name=name,
        kind=kind,
        path=path,
        provider=provider,
        enabled=_read_enabled_flag(raw_source.get("enabled", True)),
        options=dict(raw_source.get("options", {})),
    )


# Block comment:
# This helper builds a default integration list from environment variables only.
def _build_env_source_integrations() -> SourceIntegrationHubConfig:
    """Build source integration config from environment variables."""
    # Line comment: read one comma-separated source list and default to the original seed loader behavior.
    raw_sources = os.getenv("SKILLSAI_SOURCE_TYPES", SOURCE_KIND_SEED_DATA)
    normalized_sources = [
        _normalize_source_kind(raw_source)
        for raw_source in raw_sources.split(",")
        if raw_source.strip()
    ]
    integrations: list[SourceIntegration] = []
    if SOURCE_KIND_SEED_DATA in normalized_sources:
        # Line comment: preserve legacy seed-data loading as the default integration.
        integrations.append(
            SourceIntegration(
                name="seed-data",
                kind=SOURCE_KIND_SEED_DATA,
                path=resolve_seed_data_dir(),
                provider="seed",
            )
        )
    if SOURCE_KIND_CUSTOMER_RECORDS in normalized_sources:
        # Line comment: allow a simple provider override for HRIS-style customer data.
        integrations.append(
            SourceIntegration(
                name=os.getenv("SKILLSAI_CUSTOMER_SOURCE", "workday").strip() or "workday",
                kind=SOURCE_KIND_CUSTOMER_RECORDS,
                path=resolve_customer_records_dir(),
                provider=os.getenv("SKILLSAI_CUSTOMER_SOURCE", "workday").strip() or "workday",
            )
        )
    # Line comment: return an immutable wrapper so callers can reuse the resolved config safely.
    return SourceIntegrationHubConfig(sources=tuple(integrations))


# Block comment:
# This helper reads source integration config from disk or environment defaults.
def read_source_integration_config(config_path: Path | None = None) -> SourceIntegrationHubConfig:
    """Read source integration hub configuration from JSON or environment."""
    # Line comment: prefer an explicit function argument, then the matching environment variable.
    effective_config_path = config_path or resolve_source_config_path()
    if effective_config_path is None:
        return _build_env_source_integrations()
    if not effective_config_path.exists():
        # Line comment: return an empty config when an explicit config file path is missing.
        return SourceIntegrationHubConfig(sources=tuple())
    raw_payload = json.loads(effective_config_path.read_text(encoding="utf-8"))
    base_dir = effective_config_path.parent
    # Line comment: build typed source entries in the order declared by the config file.
    sources = tuple(
        _build_source_integration(dict(raw_source), base_dir)
        for raw_source in list(raw_payload.get("sources", []))
    )
    return SourceIntegrationHubConfig(sources=sources)


# Block comment:
# This helper loads one JSON seed file into a Python dictionary payload.
def _read_seed_json(seed_data_dir: Path, relative_path: str) -> dict[str, Any]:
    """Read and parse one JSON document from the seed-data tree."""
    # Line comment: build an absolute file path inside the configured seed-data folder.
    target_path = seed_data_dir / relative_path
    # Line comment: parse the JSON document into an in-memory Python structure.
    return json.loads(target_path.read_text(encoding="utf-8"))


# Block comment:
# This helper resolves the JSON document to load for one customer-record source.
def _resolve_customer_records_payload_path(source: SourceIntegration) -> Path:
    """Resolve the JSON payload path for one customer-record source."""
    # Line comment: allow direct file targets as well as provider directory roots.
    if source.path.is_file():
        return source.path
    provider_index = source.path / source.provider / "index.json"
    if provider_index.exists():
        return provider_index
    # Line comment: fallback to a flat index file directly under the configured root.
    return source.path / "index.json"


# Block comment:
# This helper reads one customer-record payload from the configured integration path.
def _read_customer_records_json(source: SourceIntegration) -> dict[str, Any]:
    """Read and parse one customer-record JSON document."""
    # Line comment: resolve the effective JSON file for the current provider integration.
    target_path = _resolve_customer_records_payload_path(source)
    # Line comment: parse the provider payload into an in-memory Python structure.
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
# This helper writes one customer-provided skill state into the graph, mart, and lineage stores.
def _write_customer_skill_state(
    platform: SkillsAIPlatform,
    employee_id: str,
    skill_state: dict[str, Any],
    provider: str,
    model_version: str,
) -> None:
    """Persist one customer skill-state record into the platform stores."""
    # Line comment: build the standard flat employee_id:skill_id graph key used by query paths.
    skill_id = str(skill_state["skill_id"])
    key = f"{employee_id}:{skill_id}"
    state_payload = {
        "employee_id": employee_id,
        "skill_id": skill_id,
        "proficiency": float(skill_state.get("proficiency", 0.0)),
        "confidence": float(skill_state.get("confidence", 0.0)),
        "gap": float(skill_state.get("gap", 0.0)),
        "explanation": str(skill_state.get("explanation", f"Loaded from {provider} customer records.")),
        "model_version": model_version,
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
    # Line comment: mark the source provider in lineage metadata for governance views.
    platform.stores.put(
        "meta",
        f"lineage:{key}",
        {"model_version": model_version, "source": provider},
    )


# Block comment:
# This helper extracts customer record claims while preserving provider-specific raw attributes.
def _build_customer_claims(record: dict[str, Any], provider: str, source_name: str, external_id: str) -> dict[str, Any]:
    """Build canonical claims payload from one provider record."""
    # Line comment: start with any explicitly nested claims object in the provider payload.
    explicit_claims = dict(record.get("claims", {}))
    derived_claims = {
        "source_provider": provider,
        "source_name": source_name,
        "external_id": external_id,
    }
    for field_name in [
        "department",
        "location",
        "email",
        "manager_id",
        "job_profile",
        "title",
        "employment_status",
        "cost_center",
    ]:
        # Line comment: surface common HRIS fields when the provider includes them directly.
        if field_name in record:
            derived_claims[field_name] = record[field_name]
    # Line comment: merge provider-derived defaults underneath explicit claims so config can override.
    return {**derived_claims, **explicit_claims}


# Block comment:
# This helper loads one customer-record integration into the platform stores.
def _load_customer_records_source(platform: SkillsAIPlatform, source: SourceIntegration) -> list[str]:
    """Load one customer-record payload into the backend platform stores."""
    # Line comment: parse the configured provider payload and capture default tenant/model metadata.
    customer_payload = _read_customer_records_json(source)
    tenant_id = str(customer_payload.get("tenant_id", "default-tenant"))
    model_version = str(customer_payload.get("model_version", f"{source.provider}-customer-records"))
    record_items = customer_payload.get("records") or customer_payload.get("employees") or customer_payload.get("workers") or []
    if customer_payload.get("taxonomy"):
        # Line comment: publish provider-supplied taxonomy when customer records include it.
        taxonomy = dict(customer_payload.get("taxonomy", {}))
        platform.core_intelligence.taxonomy.publish_taxonomy_version(
            platform.stores,
            version=str(taxonomy.get("active_version", model_version)),
            ontology={"skills": list(taxonomy.get("skills", []))},
            job_mappings=dict(taxonomy.get("job_mappings", {})),
            proficiency_scales={"default": list(DEFAULT_PROFICIENCY_SCALE)},
        )
    for raw_record in list(record_items):
        # Line comment: normalize provider aliases for canonical employee and external identifiers.
        record = dict(raw_record)
        employee_id = str(
            record.get("employee_id")
            or record.get("actor_id")
            or record.get("person_id")
            or record.get("worker_id")
            or record.get("id")
            or ""
        )
        if not employee_id:
            continue
        external_id = str(
            record.get("external_id")
            or record.get("worker_id")
            or record.get("associate_id")
            or record.get("source_id")
            or record.get("id")
            or employee_id
        )
        claims = _build_customer_claims(record, source.provider, source.name, external_id)
        # Line comment: create the canonical identity record and optional external identity link.
        platform.identity_mapper.upsert_identity(
            employee_id,
            {
                "tenant_id": record.get("tenant_id", tenant_id),
                "roles": list(record.get("roles", ["employee"])),
                "claims": claims,
            },
        )
        if external_id and external_id != employee_id:
            platform.identity_mapper.link_identity(external_id, employee_id)
        for skill_state in list(record.get("skill_states") or record.get("skills") or []):
            # Line comment: persist customer-provided skill states using the same read-model shape as seed data.
            _write_customer_skill_state(platform, employee_id, dict(skill_state), source.provider, model_version)
        recommendations = list(
            record.get("recommendations")
            or dict(record.get("coaching", {})).get("recommendations", [])
        )
        if recommendations:
            # Line comment: expose customer coaching recommendations through the activation read path.
            platform.stores.put(
                "cache",
                f"activation:{employee_id}",
                {"employee_id": employee_id, "recommendations": recommendations},
            )
    for assessment_package in list(customer_payload.get("assessment_packages", [])):
        # Line comment: support optional provider-supplied assessment packages in the same shape as seed data.
        definition = {
            "sections": list(assessment_package.get("blueprint", {}).get("sections", [])),
            "duration_min": assessment_package.get("blueprint", {}).get("duration_min", 30),
            "items": list(assessment_package.get("items", [])),
            "rubric": dict(assessment_package.get("rubric", {})),
            "blueprint": dict(assessment_package.get("blueprint", {})),
            "version": assessment_package.get("version", 1),
        }
        assessment_id = str(assessment_package["assessment_id"])
        platform.assessments.publish_assessment(assessment_id, definition=definition)
        imported_version = int(assessment_package.get("version", 1))
        # Line comment: preserve the source-system version number instead of the local publish counter.
        if assessment_id in platform.stores.item_bank:
            platform.stores.item_bank[assessment_id]["version"] = imported_version
        platform.stores.meta[f"assessment:version:{assessment_id}"] = imported_version
    for attempt in list(customer_payload.get("attempts", [])):
        # Line comment: support optional provider-supplied attempts using the standard attempt read-model shape.
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
    analytics_payload = dict(customer_payload.get("analytics", {}))
    if analytics_payload:
        # Line comment: allow optional provider KPI snapshots for hybrid demo and customer data loads.
        read_models = dict(analytics_payload.get("read_models", {}))
        kpi_snapshot = dict(read_models.get("kpi_snapshot", {}))
        if kpi_snapshot:
            metric = str(kpi_snapshot.get("metric", "skill_coverage"))
            cohort = str(kpi_snapshot.get("cohort", "all"))
            platform.stores.mart[f"{metric}:{cohort}"] = kpi_snapshot.get("data", {}).get("value", 0.0)
        planning_snapshot = dict(read_models.get("planning_snapshot", {}))
        if planning_snapshot:
            cohort = str(planning_snapshot.get("cohort", "all"))
            platform.stores.mart[f"baseline:{cohort}"] = planning_snapshot.get("data", {}).get("target", 1.0)
        # Line comment: retain provider analytics metadata for admin and governance visibility.
        platform.stores.meta[f"analytics_run:{source.name}"] = analytics_payload.get("materialization_run", {})
    platform.stores.meta.setdefault("customer_record_sources", []).append(source.name)
    platform.stores.meta.setdefault("customer_record_providers", []).append(source.provider)
    # Line comment: return module names so the hub can summarize which features were hydrated.
    return ["customer-records", "identity", "core-intelligence", "activation", "assessments", "analytics"]


class SourceIntegrationHub:
    """Configuration-driven integration hub for seed and customer data sources."""

    # Block comment:
    # This initializer stores the resolved immutable integration config for later loading.
    def __init__(self, config: SourceIntegrationHubConfig):
        """Initialize the hub with a resolved source integration config."""
        # Line comment: retain the immutable source list for ordered loading.
        self._config = config

    # Block comment:
    # This method loads all configured integrations and writes a summary into platform metadata.
    def load(self, platform: SkillsAIPlatform) -> None:
        """Load all configured source integrations into the backend platform."""
        # Line comment: reset hub summary metadata before processing configured sources.
        source_summaries: list[dict[str, Any]] = []
        loaded_modules: list[str] = []
        seed_loaded = False
        any_loaded = False
        platform.stores.meta["source_data_loaded"] = False
        platform.stores.meta["source_integrations"] = []
        platform.stores.meta["source_modules"] = []
        platform.stores.meta["seed_modules"] = []
        for source in self._config.sources:
            summary = {
                "name": source.name,
                "kind": source.kind,
                "provider": source.provider,
                "path": str(source.path),
                "enabled": source.enabled,
                "status": "skipped",
                "modules": [],
            }
            if not source.enabled:
                # Line comment: record disabled sources without attempting to load them.
                summary["status"] = "disabled"
                source_summaries.append(summary)
                continue
            if not source.path.exists() and not source.path.is_file():
                # Line comment: mark missing source roots so callers can inspect why no data was loaded.
                summary["status"] = "missing"
                source_summaries.append(summary)
                continue
            if source.kind == SOURCE_KIND_SEED_DATA:
                # Line comment: load the original seed-data modules and preserve legacy metadata keys.
                platform.stores.meta["seed_data_dir"] = str(source.path)
                _load_platform_seed(platform, source.path)
                _load_identity_seed(platform, source.path)
                _load_core_seed(platform, source.path)
                _load_activation_seed(platform, source.path)
                _load_assessment_seed(platform, source.path)
                _load_analytics_seed(platform, source.path)
                summary["modules"] = list(DEFAULT_SEED_MODULES)
                summary["status"] = "loaded"
                seed_loaded = True
                any_loaded = True
            elif source.kind == SOURCE_KIND_CUSTOMER_RECORDS:
                # Line comment: load provider customer records and derive a module summary from hydrated stores.
                summary["modules"] = _load_customer_records_source(platform, source)
                summary["status"] = "loaded"
                any_loaded = True
            else:
                # Line comment: preserve unsupported source kinds in metadata rather than raising during app startup.
                summary["status"] = "unsupported"
                source_summaries.append(summary)
                continue
            loaded_modules.extend(list(summary["modules"]))
            source_summaries.append(summary)
        platform.stores.meta["source_integrations"] = source_summaries
        platform.stores.meta["source_modules"] = sorted(set(loaded_modules))
        platform.stores.meta["source_data_loaded"] = any_loaded
        # Line comment: maintain the original seed loader flags for existing callers and tests.
        platform.stores.meta["seed_data_loaded"] = seed_loaded
        platform.stores.meta["seed_modules"] = list(DEFAULT_SEED_MODULES) if seed_loaded else []


# Block comment:
# This function loads the configured source integration set into the backend platform.
def load_source_data(
    platform: SkillsAIPlatform,
    config: SourceIntegrationHubConfig | None = None,
) -> None:
    """Load configured source integrations into the backend platform."""
    # Line comment: resolve config lazily so callers can inject custom test or runtime settings.
    effective_config = config or read_source_integration_config()
    hub = SourceIntegrationHub(effective_config)
    # Line comment: delegate the full load operation to the source integration hub.
    hub.load(platform)


# Block comment:
# This compatibility wrapper preserves the original seed loader entry point for callers.
def load_seed_data(
    platform: SkillsAIPlatform,
    seed_data_dir: Path | None = None,
    source_config: SourceIntegrationHubConfig | None = None,
) -> None:
    """Load seed data and/or customer records through the source integration hub."""
    # Line comment: preserve the original explicit seed-data override behavior for tests and scripts.
    if source_config is None and seed_data_dir is not None:
        source_config = SourceIntegrationHubConfig(
            sources=(
                SourceIntegration(
                    name="seed-data",
                    kind=SOURCE_KIND_SEED_DATA,
                    path=seed_data_dir.resolve(),
                    provider="seed",
                ),
            )
        )
    # Line comment: route all loading through the config-driven integration hub.
    load_source_data(platform, config=source_config)
