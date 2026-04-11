"""Core Intelligence container implementation (taxonomy, inference, governance)."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

try:
    from ..event_bus import PlatformEventBus
    from ..models import EvidenceSignal, SkillState
    from ..stores import PlatformStores
except ImportError:
    from event_bus import PlatformEventBus
    from models import EvidenceSignal, SkillState
    from stores import PlatformStores


class TaxonomyService:
    """Implements the Level 3B taxonomy service components."""

    # Block comment:
    # The taxonomy API publishes versioned read models into cache and metadata.
    def publish_taxonomy_version(
        self,
        stores: PlatformStores,
        version: str,
        ontology: dict[str, Any],
        job_mappings: dict[str, list[str]],
        proficiency_scales: dict[str, list[str]],
    ) -> None:
        """Persist one full taxonomy version and derived cache read model."""
        # Line comment: persist versioned ontology and mappings into metadata store.
        stores.put("meta", f"taxonomy:{version}", {"ontology": ontology, "jobs": job_mappings, "scales": proficiency_scales})
        # Line comment: publish quick-read cache entry for active taxonomy version.
        stores.put("cache", "active_taxonomy_version", version)


class GovernanceService:
    """Implements the Level 3B governance service components."""

    # Block comment:
    # Consent and policy are simplified into deterministic checks with audit.
    def authorize_evidence(self, stores: PlatformStores, employee_id: str, source: str) -> bool:
        """Authorize evidence intake for one employee and source."""
        # Line comment: read consent from audit store defaults when absent.
        consent_key = f"consent:{employee_id}:{source}"
        consent_value = stores.get("cache", consent_key, True)
        # Line comment: record access decision in audit/consent store.
        stores.append(
            "audit",
            {
                "event": "AccessDecision",
                "employee_id": employee_id,
                "source": source,
                "allowed": bool(consent_value),
            },
        )
        return bool(consent_value)

    # Block comment:
    # Retention manager writes explicit retention operations into audit stream.
    def apply_retention(self, stores: PlatformStores, retention_tag: str) -> None:
        """Record a retention operation for observability and compliance."""
        # Line comment: append retention operation record into event store.
        stores.append("time_series", {"event": "RetentionOperation", "tag": retention_tag})
        # Line comment: append audit record linked to the retention tag.
        stores.append("audit", {"event": "RetentionAudit", "tag": retention_tag})


class InferenceService:
    """Implements the Level 3B inference service components."""

    def __init__(self, stores: PlatformStores, event_bus: PlatformEventBus, governance: GovernanceService):
        """Initialize inference service with stores, bus, and governance."""
        self._stores = stores
        self._event_bus = event_bus
        self._governance = governance

    # Block comment:
    # This method executes the full evidence->skill-state pipeline documented in 3B.
    def ingest_evidence(self, signal: EvidenceSignal, model_version: str = "v1") -> SkillState:
        """Run normalization, fusion, scoring, and publication for one signal."""
        # Line comment: enforce consent/policy before accepting evidence intake.
        if not self._governance.authorize_evidence(self._stores, signal.employee_id, signal.source):
            raise PermissionError("Evidence intake blocked by governance policy.")
        # Line comment: normalize to bounded signal range and carry metadata.
        normalized_value = max(0.0, min(1.0, float(signal.value)))
        # Line comment: fuse signals with prior inferred state if present.
        existing = self._stores.get("graph", f"{signal.employee_id}:{signal.skill_id}")
        prior_proficiency = float(existing["proficiency"]) if isinstance(existing, dict) and "proficiency" in existing else 0.0
        fused = (prior_proficiency + normalized_value) / 2.0
        # Line comment: estimate proficiency and confidence from fused signal and hint.
        proficiency = round(fused, 4)
        confidence = round(max(0.0, min(1.0, signal.confidence_hint * 0.7 + 0.3)), 4)
        # Line comment: detect gap against target proficiency 0.8 for demonstrative pipeline.
        gap = round(max(0.0, 0.8 - proficiency), 4)
        # Line comment: construct explanation payload for downstream UI consumers.
        explanation = f"Inferred from {signal.source} signal with fused score {proficiency:.2f}."
        state = SkillState(
            employee_id=signal.employee_id,
            skill_id=signal.skill_id,
            proficiency=proficiency,
            confidence=confidence,
            gap=gap,
            explanation=explanation,
            model_version=model_version,
        )
        # Line comment: publish inferred state across graph, stores, and audit.
        key = f"{signal.employee_id}:{signal.skill_id}"
        stores_payload = asdict(state)
        self._stores.put("graph", key, stores_payload)
        self._stores.append("time_series", {"event": "SkillStateEvent", **stores_payload})
        self._stores.put("mart", key, {"proficiency": proficiency, "confidence": confidence, "gap": gap})
        self._stores.put("meta", f"lineage:{key}", {"model_version": model_version, "source": signal.source})
        self._stores.append("audit", {"event": "InferenceAudit", "key": key, "model_version": model_version})
        self._event_bus.publish("SkillStateUpdated", {"key": key, "state": stores_payload})
        return state


class CoreIntelligenceAPI:
    """Container-level API exposing taxonomy and inference operations."""

    def __init__(self, stores: PlatformStores, event_bus: PlatformEventBus):
        """Initialize container API with component services."""
        # Line comment: keep shared store for query helper methods.
        self._stores = stores
        self.taxonomy = TaxonomyService()
        self.governance = GovernanceService()
        self.inference = InferenceService(stores, event_bus, self.governance)

    # Block comment:
    # Read path exposes inferred skill state and active taxonomy version.
    def get_skill_snapshot(self, stores: PlatformStores, employee_id: str, skill_id: str) -> dict[str, Any]:
        """Return one composed read model for employee skill state."""
        # Line comment: read graph-based inferred state for the requested pair.
        key = f"{employee_id}:{skill_id}"
        state = stores.get("graph", key, {})
        # Line comment: include active taxonomy version as response metadata.
        taxonomy_version = stores.get("cache", "active_taxonomy_version", "unversioned")
        return {"skill_state": state, "taxonomy_version": taxonomy_version}

    # Block comment:
    # This adapter preserves naming expected by federation query composition.
    def read_skill_states(self, employee_id: str) -> dict[str, Any]:
        """Read all inferred skill states for one employee."""
        # Line comment: scan graph entries keyed by employee_id:skill_id.
        results: dict[str, Any] = {}
        for key, value in self._stores.graph.items():
            if key.startswith(f"{employee_id}:"):
                results[key.split(":", 1)[1]] = value
        return results

    # Block comment:
    # This adapter accepts dict payloads used by command orchestration paths.
    def ingest_evidence(self, payload: dict[str, Any] | EvidenceSignal) -> SkillState:
        """Ingest one evidence payload and return inferred skill state."""
        # Block comment:
        # Gateway commands send dict payloads while assessments send typed signals.
        # Line comment: normalize supported payload shapes into EvidenceSignal.
        if isinstance(payload, EvidenceSignal):
            signal = payload
            model_version = "v1"
        else:
            signal = EvidenceSignal(
                employee_id=str(payload["employee_id"]),
                skill_id=str(payload["skill_id"]),
                value=float(payload["value"]),
                source=str(payload.get("source", "gateway")),
                confidence_hint=float(payload.get("confidence_hint", 0.7)),
                metadata=dict(payload.get("metadata", {})),
            )
            # Line comment: propagate optional model version from command payload.
            model_version = str(payload.get("model_version", "v1"))
        return self.inference.ingest_evidence(signal, model_version=model_version)


class CoreIntelligenceContainer(CoreIntelligenceAPI):
    """Container alias for composition root compatibility."""
