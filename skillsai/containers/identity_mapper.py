"""Identity Mapper container implementation (Level 2 container + Level 3A API)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from skillsai.models import RequestContext
from skillsai.stores import PlatformStores


@dataclass(slots=True)
class IdentityMapperAPI:
    """Provides canonical identity reads, writes, and context resolution."""

    stores: PlatformStores

    # Block comment:
    # This function creates or updates one canonical identity view in cache.
    def upsert_identity(self, actor_id: str, claims: dict[str, Any]) -> dict[str, Any]:
        """Create or update canonical identity for one actor."""
        # Line comment: derive tenant and role values from claims with defaults.
        tenant_id = str(claims.get("tenant_id", claims.get("tenant_hint", "default-tenant")))
        roles = list(claims.get("roles", ["employee"]))
        # Line comment: build canonical identity payload for the cache read model.
        record = {
            "actor_id": actor_id,
            "tenant_id": tenant_id,
            "roles": roles,
            "claims": dict(claims),
        }
        self.stores.put("cache", f"identity:{actor_id}", record)
        return record

    # Block comment:
    # This function links an external identity id to a canonical employee id.
    def link_identity(self, external_id: str, employee_id: str) -> dict[str, str]:
        """Link one external identity value to one employee identity."""
        # Line comment: persist deterministic link mapping for later lookups.
        self.stores.put("cache", f"id-link:{external_id}", employee_id)
        # Line comment: append an audit trail record for the identity link operation.
        self.stores.append(
            "audit",
            {
                "event": "IdentityLinked",
                "external_id": external_id,
                "employee_id": employee_id,
            },
        )
        return {"external_id": external_id, "employee_id": employee_id}

    # Block comment:
    # This function returns one canonical identity payload by employee id.
    def read_identity(self, employee_id: str) -> dict[str, Any]:
        """Read one canonical identity profile."""
        # Line comment: load cached identity payload or return empty record.
        return dict(self.stores.get("cache", f"identity:{employee_id}", {}))

    # Block comment:
    # This function resolves request context used by the federation gateway path.
    def resolve_context(self, actor_id: str, feature_flags: dict[str, bool]) -> RequestContext:
        """Resolve one actor context for tenant-scoped request handling."""
        # Line comment: load or lazily initialize canonical identity state.
        cached = self.stores.get("cache", f"identity:{actor_id}", None)
        if cached is None:
            cached = self.upsert_identity(actor_id, {"tenant_id": "default-tenant", "roles": ["employee"]})
        # Line comment: convert cached identity payload into typed request context.
        return RequestContext(
            actor_id=actor_id,
            tenant_id=str(cached.get("tenant_id", "default-tenant")),
            roles=list(cached.get("roles", ["employee"])),
            claims=dict(cached.get("claims", {})),
            feature_flags=dict(feature_flags),
        )
