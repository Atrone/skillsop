"""Source integration hub for loading seed data and customer record data."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen

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
DEFAULT_WORKDAY_API_BASE_URL = "http://localhost:8106/api/v1/acme"
DEFAULT_WORKDAY_MODEL_VERSION = "workday-api-v1"
DEFAULT_WORKDAY_TAXONOMY_VERSION = "workday-api-taxonomy"
DEFAULT_WORKDAY_TENANT_ID = "acme-tenant"
WORKDAY_PROFICIENCY_VALUES = {
    "advanced": 1.0,
    "intermediate": 0.8,
    "beginner": 0.6,
    "novice": 0.4,
}


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
# This helper identifies Workday customer sources that should load over HTTP instead of disk.
def _source_uses_workday_api(source: SourceIntegration) -> bool:
    """Return whether one source should load from the Workday mock API."""
    # Line comment: normalize provider name so config aliases remain case-insensitive.
    return source.kind == SOURCE_KIND_CUSTOMER_RECORDS and source.provider.strip().lower() == "workday"


# Block comment:
# This helper centralizes source availability checks for both local folders and remote Workday APIs.
def _source_has_loadable_input(source: SourceIntegration) -> bool:
    """Return whether one source has enough input information to attempt loading."""
    # Line comment: allow Workday API integrations to load even when the legacy folder path is absent.
    if _source_uses_workday_api(source):
        return True
    # Line comment: require an existing file or directory for all local-data integrations.
    return source.path.exists() or source.path.is_file()


# Block comment:
# This helper resolves the base URL for the Workday mock API from source options or environment.
def _resolve_workday_api_base_url(source: SourceIntegration) -> str:
    """Resolve the effective base URL for one Workday API integration."""
    # Line comment: prefer explicit source options before falling back to environment defaults.
    configured_base_url = str(
        source.options.get("base_url", os.getenv("SKILLSAI_WORKDAY_API_BASE_URL", DEFAULT_WORKDAY_API_BASE_URL))
    ).strip()
    normalized_base_url = configured_base_url.rstrip("/")
    # Line comment: trim any explicit index document suffix so callers can append REST resource paths cleanly.
    if normalized_base_url.endswith("/index.json"):
        normalized_base_url = normalized_base_url[: -len("/index.json")]
    return normalized_base_url


# Block comment:
# This helper fetches and parses one JSON document from a remote HTTP endpoint.
def _fetch_remote_json(url: str) -> dict[str, Any]:
    """Fetch one JSON payload from a remote URL."""
    # Line comment: ask the remote service for JSON explicitly so the mock and real APIs share one code path.
    request = Request(url, headers={"Accept": "application/json"})
    # Line comment: decode the response body into a Python dictionary for downstream transforms.
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


# Block comment:
# This helper normalizes free-text Workday labels into stable slug identifiers.
def _slugify_workday_value(raw_value: str) -> str:
    """Normalize one free-text Workday label into a slug identifier."""
    # Line comment: replace non-alphanumeric groups so generated ids stay deterministic and ASCII-safe.
    normalized_value = re.sub(r"[^a-z0-9]+", "_", raw_value.strip().lower())
    return normalized_value.strip("_")


# Block comment:
# This helper converts one Workday skill label into the canonical skill id format used by the platform.
def _build_workday_skill_id(skill_name: str) -> str:
    """Build one canonical skill identifier from a Workday skill label."""
    # Line comment: fall back to a placeholder slug only when the API omits a descriptor entirely.
    skill_slug = _slugify_workday_value(skill_name) or "unknown_skill"
    return f"skill:{skill_slug}"


# Block comment:
# This helper fetches the full Workday mock API payload set needed by the source integration loader.
def _fetch_workday_api_payload(source: SourceIntegration) -> dict[str, Any]:
    """Fetch and normalize the Workday API resources used during platform hydration."""
    # Line comment: start from the tenant-scoped base endpoint so resource paths can be discovered dynamically.
    base_url = _resolve_workday_api_base_url(source)
    root_payload = _fetch_remote_json(base_url)
    resource_paths = {
        str(resource.get("name", "")).strip().lower(): str(resource.get("path", ""))
        for resource in list(root_payload.get("resources", []))
        if isinstance(resource, dict)
    }
    # Line comment: fetch top-level collections from discovered resource paths or stable Workday-style fallbacks.
    workers_path = resource_paths.get("workers", f"{base_url}/workers")
    jobs_path = resource_paths.get("jobs", f"{base_url}/jobs")
    organizations_path = resource_paths.get("organizations", f"{base_url}/organizations")
    locations_path = resource_paths.get("locations", f"{base_url}/locations")
    worker_collection = _fetch_remote_json(urljoin(f"{base_url}/", workers_path))
    job_collection = _fetch_remote_json(urljoin(f"{base_url}/", jobs_path))
    organization_collection = _fetch_remote_json(urljoin(f"{base_url}/", organizations_path))
    location_collection = _fetch_remote_json(urljoin(f"{base_url}/", locations_path))
    jobs_by_id: dict[str, dict[str, Any]] = {}
    organizations_by_id: dict[str, dict[str, Any]] = {}
    locations_by_id: dict[str, dict[str, Any]] = {}
    workers: list[dict[str, Any]] = []
    for job_summary in list(job_collection.get("data", [])):
        # Line comment: resolve each referenced job so downstream loaders can inspect skills and levels.
        job_id = str(job_summary.get("id", "")).strip()
        if not job_id:
            continue
        jobs_by_id[job_id] = _fetch_remote_json(urljoin(f"{base_url}/", f"jobs/{quote(job_id)}"))
    for organization_summary in list(organization_collection.get("data", [])):
        # Line comment: resolve each organization so staffing and cohort metadata can seed analytics inputs.
        organization_id = str(organization_summary.get("id", "")).strip()
        if not organization_id:
            continue
        organizations_by_id[organization_id] = _fetch_remote_json(
            urljoin(f"{base_url}/", f"organizations/{quote(organization_id)}")
        )
    for location_summary in list(location_collection.get("data", [])):
        # Line comment: resolve each location so identity claims can include canonical site metadata.
        location_id = str(location_summary.get("id", "")).strip()
        if not location_id:
            continue
        locations_by_id[location_id] = _fetch_remote_json(urljoin(f"{base_url}/", f"locations/{quote(location_id)}"))
    for worker_summary in list(worker_collection.get("data", [])):
        # Line comment: follow worker links so the loader consumes the same detail endpoints as an integration client.
        worker_id = str(worker_summary.get("id", "")).strip()
        if not worker_id:
            continue
        worker_links = {
            str(link.get("rel", "")).strip().lower(): str(link.get("href", ""))
            for link in list(worker_summary.get("links", []))
            if isinstance(link, dict)
        }
        detail_payload = _fetch_remote_json(urljoin(f"{base_url}/", worker_links.get("self", f"workers/{quote(worker_id)}")))
        basic_payload = _fetch_remote_json(
            urljoin(f"{base_url}/", worker_links.get("basic", f"workers/{quote(worker_id)}/basic"))
        )
        talent_payload = _fetch_remote_json(
            urljoin(f"{base_url}/", worker_links.get("talent", f"workers/{quote(worker_id)}/talent"))
        )
        workers.append(
            {
                "summary": dict(worker_summary),
                "detail": detail_payload,
                "basic": basic_payload,
                "talent": talent_payload,
            }
        )
    return {
        "base_url": base_url,
        "root": root_payload,
        "workers": workers,
        "jobs": jobs_by_id,
        "organizations": organizations_by_id,
        "locations": locations_by_id,
    }


# Block comment:
# This helper waits for any analytics workflow jobs that were queued by Workday-derived events.
def _wait_for_workday_workflow_jobs(platform: SkillsAIPlatform) -> None:
    """Wait until all currently queued analytics workflow jobs finish."""
    # Line comment: copy the current job list once so this wait only covers jobs triggered during the current load cycle.
    pending_jobs = list(platform.analytics.list_workflow_jobs(limit=200))
    for job in pending_jobs:
        # Line comment: block only on jobs that are still in flight when the helper is called.
        if str(job.get("state", "")) in {"queued", "running"}:
            platform.analytics.wait_for_workflow_job(str(job["job_id"]))


# Block comment:
# This helper loads one Workday API integration by driving the platform's container computations from mock API payloads.
def _load_workday_customer_records_source(platform: SkillsAIPlatform, source: SourceIntegration) -> list[str]:
    """Load one Workday customer source using remote API payloads and container mutation paths."""
    # Line comment: fetch the full Workday payload set before mutating stores so transforms stay deterministic.
    workday_payload = _fetch_workday_api_payload(source)
    root_payload = dict(workday_payload.get("root", {}))
    worker_payloads = list(workday_payload.get("workers", []))
    tenant_id = str(source.options.get("tenant_id", DEFAULT_WORKDAY_TENANT_ID))
    model_version = str(source.options.get("model_version", DEFAULT_WORKDAY_MODEL_VERSION))
    taxonomy_version = str(source.options.get("taxonomy_version", DEFAULT_WORKDAY_TAXONOMY_VERSION))
    # Line comment: derive taxonomy skills and job mappings from the same Workday talent and job detail endpoints.
    taxonomy_skills: dict[str, dict[str, Any]] = {}
    job_mappings: dict[str, list[str]] = {}
    for worker_payload in worker_payloads:
        talent_payload = dict(worker_payload.get("talent", {}))
        detail_payload = dict(worker_payload.get("detail", {}))
        job_profile = dict(detail_payload.get("jobProfile", {}))
        job_detail = dict(workday_payload.get("jobs", {}).get(str(job_profile.get("id", "")), {}))
        job_descriptor = str(job_detail.get("descriptor") or job_profile.get("descriptor") or "unknown-job")
        job_key = _slugify_workday_value(job_descriptor) or "unknown_job"
        mapped_skill_ids: list[str] = []
        for skill in list(talent_payload.get("skills", [])):
            # Line comment: publish each talent endpoint skill into the active taxonomy version.
            skill_name = str(skill.get("descriptor") or skill.get("name") or skill.get("id") or "Unknown Skill")
            skill_id = _build_workday_skill_id(skill_name)
            taxonomy_skills[skill_id] = {"id": skill_id, "descriptor": skill_name}
            mapped_skill_ids.append(skill_id)
        if mapped_skill_ids:
            job_mappings[job_key] = sorted(set(mapped_skill_ids))
    platform.core_intelligence.taxonomy.publish_taxonomy_version(
        platform.stores,
        version=taxonomy_version,
        ontology={"skills": list(taxonomy_skills.values())},
        job_mappings=job_mappings,
        proficiency_scales={"default": list(DEFAULT_PROFICIENCY_SCALE)},
    )
    platform.stores.meta[f"workday_api:{source.name}"] = {
        "base_url": str(workday_payload.get("base_url", "")),
        "tenant": str(root_payload.get("tenant", "acme")),
        "worker_count": len(worker_payloads),
        "job_count": len(workday_payload.get("jobs", {})),
        "organization_count": len(workday_payload.get("organizations", {})),
        "location_count": len(workday_payload.get("locations", {})),
    }
    derived_cohorts: list[str] = []
    for worker_payload in worker_payloads:
        # Line comment: collect detail documents used to build identity, inference, and activation inputs.
        summary_payload = dict(worker_payload.get("summary", {}))
        detail_payload = dict(worker_payload.get("detail", {}))
        basic_payload = dict(worker_payload.get("basic", {}))
        talent_payload = dict(worker_payload.get("talent", {}))
        job_profile = dict(detail_payload.get("jobProfile", {}))
        organization_payload = dict((detail_payload.get("organizations") or [{}])[0])
        if not organization_payload:
            organization_payload = dict(summary_payload.get("supervisoryOrganization", {}))
        location_payload = dict(detail_payload.get("location", {}))
        if not location_payload:
            location_payload = dict(summary_payload.get("location", {}))
        job_detail = dict(workday_payload.get("jobs", {}).get(str(job_profile.get("id", "")), {}))
        organization_detail = dict(workday_payload.get("organizations", {}).get(str(organization_payload.get("id", "")), {}))
        location_detail = dict(workday_payload.get("locations", {}).get(str(location_payload.get("id", "")), {}))
        employee_number = str(
            basic_payload.get("employeeId")
            or detail_payload.get("employeeId")
            or summary_payload.get("employeeId")
            or detail_payload.get("id")
            or "unknown"
        )
        employee_id = str(source.options.get("employee_id_prefix", "emp-")) + employee_number
        workday_worker_id = str(detail_payload.get("id") or summary_payload.get("id") or employee_id)
        cohort_value = str(
            organization_payload.get("id")
            or organization_detail.get("id")
            or organization_payload.get("descriptor")
            or "all"
        )
        cohort = _slugify_workday_value(cohort_value) or "all"
        derived_cohorts.append(cohort)
        worker_record = {
            "employee_id": employee_id,
            "worker_id": workday_worker_id,
            "external_id": f"workday:{employee_number}",
            "tenant_id": tenant_id,
            "roles": list(source.options.get("roles", ["employee"])),
            "department": str(organization_payload.get("descriptor") or organization_detail.get("descriptor") or "Unknown"),
            "location": str(location_payload.get("descriptor") or location_detail.get("descriptor") or "Unknown"),
            "email": str(
                basic_payload.get("workEmail")
                or dict(detail_payload.get("personal", {})).get("email")
                or f"{employee_number}@example.com"
            ),
            "manager_id": str(dict(detail_payload.get("manager", {})).get("id", "")),
            "job_profile": str(job_profile.get("descriptor") or job_detail.get("descriptor") or "Unknown"),
            "title": str(
                dict(detail_payload.get("employment", {})).get("businessTitle")
                or summary_payload.get("businessTitle")
                or "Unknown"
            ),
            "employment_status": "active" if bool(dict(detail_payload.get("employment", {})).get("active", True)) else "inactive",
            "cost_center": str(dict(organization_detail.get("company", {})).get("name", "Unknown")),
            "claims": {
                "worker_descriptor": str(detail_payload.get("descriptor") or summary_payload.get("descriptor") or employee_id),
                "worker_type": str(dict(detail_payload.get("employment", {})).get("workerType", "Employee")),
                "workday_employee_id": employee_number,
                "location_timezone": str(location_detail.get("timezone", "")),
            },
        }
        claims = _build_customer_claims(worker_record, source.provider, source.name, str(worker_record["external_id"]))
        platform.identity_mapper.upsert_identity(
            employee_id,
            {
                "tenant_id": tenant_id,
                "roles": list(worker_record.get("roles", ["employee"])),
                "claims": claims,
            },
        )
        platform.identity_mapper.link_identity(str(worker_record["external_id"]), employee_id)
        if workday_worker_id and workday_worker_id != employee_id:
            # Line comment: keep native Workday worker ids resolvable for REST and SSO-style token flows.
            platform.identity_mapper.link_identity(workday_worker_id, employee_id)
        job_skills = {
            _slugify_workday_value(str(skill_name))
            for skill_name in list(job_detail.get("skills", []))
        }
        for skill in list(talent_payload.get("skills", [])):
            # Line comment: ingest Workday talent skills as evidence so core intelligence computes graph and mart state itself.
            skill_name = str(skill.get("descriptor") or skill.get("name") or skill.get("id") or "Unknown Skill")
            skill_id = _build_workday_skill_id(skill_name)
            proficiency_label = str(skill.get("proficiency", "intermediate")).strip().lower()
            talent_value = float(WORKDAY_PROFICIENCY_VALUES.get(proficiency_label, 0.7))
            platform.core_intelligence.ingest_evidence(
                {
                    "employee_id": employee_id,
                    "skill_id": skill_id,
                    "value": talent_value,
                    "source": "workday.talent",
                    "confidence_hint": 0.9,
                    "metadata": {
                        "worker_id": workday_worker_id,
                        "skill_label": skill_name,
                        "proficiency": proficiency_label,
                    },
                    "model_version": model_version,
                }
            )
            if _slugify_workday_value(skill_name) in job_skills:
                # Line comment: ingest a second Workday job-alignment signal so graph-backed activation reads have richer inputs.
                platform.core_intelligence.ingest_evidence(
                    {
                        "employee_id": employee_id,
                        "skill_id": skill_id,
                        "value": min(1.0, talent_value + 0.1),
                        "source": "workday.job_profile",
                        "confidence_hint": 0.8,
                        "metadata": {
                            "job_profile": str(worker_record["job_profile"]),
                            "skill_label": skill_name,
                        },
                        "model_version": model_version,
                    }
                )
        context = platform.identity_mapper.resolve_context(employee_id, {})
        activation_read = platform.activation_services.read(context, {"employee_id": employee_id})
        recommendations = list(activation_read.get("recommendations", []))
        if recommendations:
            # Line comment: record one derived coaching action so activation marts and analytics time-series update through APIs.
            platform.activation_services.act(
                context,
                {
                    "employee_id": employee_id,
                    "action_type": "coaching",
                    "skill_id": str(recommendations[0].get("skill_id", "")),
                    "outcome": "accepted",
                },
            )
    # Line comment: wait for event-driven analytics jobs before installing KPI definitions to keep the final materialization deterministic.
    _wait_for_workday_workflow_jobs(platform)
    primary_organization = next(iter(workday_payload.get("organizations", {}).values()), {})
    headcount = float(dict(primary_organization.get("staffing", {})).get("headcount", max(len(worker_payloads), 1)))
    open_positions = float(dict(primary_organization.get("staffing", {})).get("openPositions", 0))
    unique_skill_count = max(len(taxonomy_skills), 1)
    primary_cohort = derived_cohorts[0] if derived_cohorts else "all"
    platform.stores.meta["kpi_definitions"] = {
        "skill_coverage": {
            "cohort": primary_cohort,
            "multiplier": round(unique_skill_count / max(headcount, 1.0), 4),
        },
        "trend.skill_coverage": {
            "cohort": primary_cohort,
            "multiplier": round((unique_skill_count + open_positions) / max(headcount, 1.0), 4),
        },
        "activation.coaching.accepted": {
            "cohort": primary_cohort,
            "multiplier": round(max(len(worker_payloads), 1) / max(headcount, 1.0), 4),
        },
    }
    materialization_result = platform.analytics.trigger_materialization(
        trigger=f"workday:{primary_cohort}",
        wait_for_completion=True,
    )
    platform.stores.meta[f"analytics_run:{source.name}"] = dict(materialization_result.get("run", {}))
    platform.stores.meta.setdefault("customer_record_sources", []).append(source.name)
    platform.stores.meta.setdefault("customer_record_providers", []).append(source.provider)
    # Line comment: report the modules that were hydrated through Workday API-driven container computations.
    return ["customer-records", "identity", "core-intelligence", "activation", "analytics"]


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
    # Line comment: route Workday sources through the API-backed container computation path.
    if _source_uses_workday_api(source):
        return _load_workday_customer_records_source(platform, source)
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
            if not _source_has_loadable_input(source):
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
