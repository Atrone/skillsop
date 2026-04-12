"""Federation gateway container and components (C4 Level 3A)."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

try:
    from ..models import PlatformRequest, PlatformResponse, RequestContext
    from ..stores import PlatformStores
except ImportError:
    from models import PlatformRequest, PlatformResponse, RequestContext
    from stores import PlatformStores


@dataclass
class WebAPIEntry:
    """Receives inbound user/API requests."""

    # Block comment:
    # This component is the entry adapter and can normalize inputs.
    def accept(self, request: PlatformRequest) -> PlatformRequest:
        """Accept and return the inbound request unchanged."""
        # Line comment: return request after edge acceptance.
        return request


@dataclass
class RateLimiter:
    """Applies simple per-actor rate limiting."""

    stores: PlatformStores
    max_requests: int = 1000

    # Block comment:
    # This helper reads the effective request budget from environment or defaults.
    def _resolve_request_budget(self) -> int:
        """Return the configured per-window request budget for one actor."""
        # Line comment: allow operators to override the default budget for local development.
        raw_limit = os.getenv("SKILLSAI_RATE_LIMIT_MAX_REQUESTS", "").strip()
        if raw_limit:
            return int(raw_limit)
        # Line comment: use a more forgiving default so the frontend can load multiple panels safely.
        return int(self.max_requests)

    # Block comment:
    # This helper reads the effective rate-limit window size from environment or defaults.
    def _resolve_window_seconds(self) -> int:
        """Return the configured rolling window length in seconds."""
        # Line comment: allow operators to tune how often actor counters reset.
        raw_window = os.getenv("SKILLSAI_RATE_LIMIT_WINDOW_SECONDS", "").strip()
        if raw_window:
            return int(raw_window)
        # Line comment: reset counters every minute for predictable local behavior.
        return 60

    # Block comment:
    # This implementation tracks per-actor counters in cache using a resettable time window.
    def throttle(self, actor_id: str) -> None:
        """Raise if actor has exceeded a simplistic fixed request budget."""
        # Line comment: resolve current actor request budget and disable limiting when requested.
        request_budget = self._resolve_request_budget()
        if request_budget <= 0:
            return
        # Line comment: resolve current actor counter entry from the shared cache store.
        key = f"rate:{actor_id}"
        current_epoch = int(time.time())
        window_seconds = self._resolve_window_seconds()
        cached_entry = self.stores.cache.get(key, {})
        if isinstance(cached_entry, dict):
            current_count = int(cached_entry.get("count", 0))
            window_started_at = int(cached_entry.get("window_started_at", current_epoch))
        else:
            # Line comment: preserve compatibility with older integer-only counter entries.
            current_count = int(cached_entry or 0)
            window_started_at = current_epoch
        # Line comment: reset the counter when the configured window has elapsed.
        if current_epoch - window_started_at >= window_seconds:
            current_count = 0
            window_started_at = current_epoch
        if current_count >= request_budget:
            raise PermissionError("Rate limit exceeded.")
        # Line comment: increment and persist the current windowed actor counter.
        self.stores.cache[key] = {
            "count": current_count + 1,
            "window_started_at": window_started_at,
        }


@dataclass
class AuthAdapter:
    """Validates tokens/claims through an identity provider boundary."""

    stores: PlatformStores | None = None

    # Block comment:
    # This helper resolves one external identity value to a canonical actor id.
    def _resolve_external_actor(self, external_id: str) -> str | None:
        """Resolve one external identifier into a canonical actor id."""
        # Line comment: return early when cache-backed identity links are unavailable.
        if self.stores is None:
            return None
        # Line comment: try exact external ids plus common provider prefixes for compatibility.
        lookup_candidates = [external_id]
        if ":" not in external_id:
            lookup_candidates.extend([f"workday:{external_id}", f"hris:{external_id}"])
        for candidate in lookup_candidates:
            linked_actor = self.stores.get("cache", f"id-link:{candidate}", None)
            if isinstance(linked_actor, str) and linked_actor:
                return linked_actor
        return None

    # Block comment:
    # This helper reads role claims from canonical identity cache records.
    def _read_actor_roles(self, actor_id: str) -> list[str]:
        """Read canonical role list for one actor id."""
        # Line comment: fallback to employee role when store-backed identity data is unavailable.
        if self.stores is None:
            return ["employee"]
        identity_record = self.stores.get("cache", f"identity:{actor_id}", {})
        if isinstance(identity_record, dict):
            roles = identity_record.get("roles", ["employee"])
            if isinstance(roles, list) and roles:
                return [str(role) for role in roles]
        return ["employee"]

    # Block comment:
    # This helper resolves tenant hints from identity cache or explicit token hints.
    def _read_actor_tenant(self, actor_id: str, fallback_tenant: str) -> str:
        """Resolve tenant id for one actor with fallback behavior."""
        # Line comment: return fallback tenant when identity store is not configured.
        if self.stores is None:
            return fallback_tenant
        identity_record = self.stores.get("cache", f"identity:{actor_id}", {})
        if isinstance(identity_record, dict) and identity_record.get("tenant_id"):
            return str(identity_record.get("tenant_id"))
        return fallback_tenant

    # Block comment:
    # This method models token/claim verification from an IdP.
    def authenticate(self, token: str, actor_id: str | None = None) -> dict[str, object]:
        """Return normalized claims for a non-empty bearer token."""
        # Line comment: reject empty tokens as unauthorized.
        if not token:
            raise PermissionError("Missing authentication token.")
        # Line comment: support Workday SSO token flow via canonical external identity links.
        if token.startswith("workday:"):
            token_parts = token.split(":")
            if len(token_parts) < 2 or not token_parts[1]:
                raise PermissionError("Invalid Workday authentication token.")
            external_subject = token_parts[1]
            tenant_hint = token_parts[2] if len(token_parts) > 2 and token_parts[2] else "default"
            resolved_actor = self._resolve_external_actor(external_subject)
            if resolved_actor is None and actor_id:
                # Line comment: allow canonical actor fallback when caller already provides a known identity.
                if self.stores is not None and self.stores.get("cache", f"identity:{actor_id}", None):
                    resolved_actor = actor_id
            if not resolved_actor:
                raise PermissionError("Unknown Workday identity.")
            tenant_hint = self._read_actor_tenant(resolved_actor, tenant_hint)
            return {
                "sub": resolved_actor,
                "actor_id": resolved_actor,
                "tenant_hint": tenant_hint,
                "roles": self._read_actor_roles(resolved_actor),
                "auth_provider": "workday",
                "external_subject": external_subject,
            }
        # Line comment: allow opaque service tokens and bind them to the caller-provided actor context.
        if ":" not in token:
            if actor_id is None:
                return {"sub": token, "tenant_hint": "default"}
            return {"sub": actor_id, "actor_id": actor_id, "tenant_hint": "default"}
        # Line comment: parse legacy subject:tenant tokens with optional actor consistency checks.
        parts = token.split(":")
        claims: dict[str, object] = {"sub": parts[0], "tenant_hint": parts[1] if len(parts) > 1 else "default"}
        if actor_id is None:
            return claims
        if actor_id != parts[0]:
            linked_actor = self._resolve_external_actor(parts[0])
            if linked_actor != actor_id:
                raise PermissionError("Token subject does not match actor context.")
        claims["actor_id"] = actor_id
        claims["roles"] = self._read_actor_roles(actor_id)
        return claims


@dataclass
class TenantResolver:
    """Resolves tenant context for requests."""

    # Block comment:
    # The resolver chooses tenant from claims with a fallback.
    def resolve(self, claims: dict[str, object]) -> str:
        """Resolve tenant id from auth claims."""
        # Line comment: return explicit tenant hint or default tenant.
        tenant = claims.get("tenant_hint", "default")
        return str(tenant)


@dataclass
class SessionContextBuilder:
    """Builds user session context for downstream components."""

    # Block comment:
    # This creates a request context shared by routing and policies.
    def build(
        self,
        actor_id: str,
        tenant_id: str,
        claims: dict[str, object],
        flags: dict[str, bool],
    ) -> RequestContext:
        """Create canonical request context object."""
        # Line comment: derive role list with a default user role.
        roles = ["user"] if actor_id else []
        return RequestContext(
            actor_id=actor_id,
            tenant_id=tenant_id,
            roles=roles,
            claims=claims,
            feature_flags=flags,
        )


@dataclass
class FeatureFlagEvaluator:
    """Evaluates feature flags given request context."""

    stores: PlatformStores

    # Block comment:
    # Feature flags are tenant-scoped values in cache.
    def evaluate(self, tenant_id: str) -> dict[str, bool]:
        """Return merged platform feature flags for the tenant."""
        # Line comment: load per-tenant flags or fallback defaults.
        key = f"flags:{tenant_id}"
        tenant_flags = self.stores.cache.get(key, {})
        base_flags = {"assessments_enabled": True, "analytics_enabled": True}
        return {**base_flags, **tenant_flags}


@dataclass
class QueryComposer:
    """Handles read path composition to downstream APIs."""

    # Block comment:
    # This helper resolves whether one request context can access cross-user records.
    def _is_privileged_actor(self, context: RequestContext | None) -> bool:
        """Return whether one actor context can read other users' records."""
        # Line comment: skip authorization when no request context was supplied by the caller.
        if context is None:
            return True
        return any(role in {"manager", "admin"} for role in context.roles)

    # Block comment:
    # This helper resolves the target employee id from payload or current actor context.
    def _resolve_target_employee_id(self, payload: dict[str, object], context: RequestContext | None) -> str:
        """Resolve one employee id target for user-scoped query routes."""
        # Line comment: prefer explicit payload values to support manager/admin queries.
        if "employee_id" in payload:
            return str(payload["employee_id"])
        if context is not None and context.actor_id:
            # Line comment: default to authenticated actor when the payload omits employee id.
            return str(context.actor_id)
        raise ValueError("employee_id is required for this route.")

    # Block comment:
    # This helper enforces actor-level access controls for user-scoped query routes.
    def _authorize_employee_access(self, employee_id: str, context: RequestContext | None) -> None:
        """Authorize one actor context to access one employee id."""
        # Line comment: allow legacy caller paths that do not provide a request context.
        if context is None:
            return
        if employee_id == context.actor_id:
            return
        if self._is_privileged_actor(context):
            return
        raise PermissionError("Actor cannot access records for another employee.")

    # Block comment:
    # This helper summarizes governance and audit state for frontend governance views.
    def _build_governance_summary(self, stores: PlatformStores) -> dict[str, object]:
        """Build a governance-oriented summary from shared platform stores."""
        # Line comment: expose recent audit items in reverse chronological order.
        latest_audit_events = list(reversed(stores.audit[-5:]))
        return {
            "audit_count": len(stores.audit),
            "time_series_count": len(stores.time_series),
            "active_taxonomy_version": stores.cache.get("active_taxonomy_version", "unversioned"),
            "seed_data_dir": stores.meta.get("seed_data_dir", ""),
            "latest_audit_events": latest_audit_events,
        }

    # Block comment:
    # This helper summarizes seed-data and loaded backend modules for admin views.
    def _build_admin_summary(self, stores: PlatformStores) -> dict[str, object]:
        """Build an admin-oriented summary from seeded platform metadata."""
        # Line comment: collect stable counts and metadata from the shared stores.
        identity_count = sum(1 for key in stores.cache if key.startswith("identity:"))
        request_samples = stores.meta.get("seed_platform_request_samples", [])
        workflow_jobs = list(reversed(list(stores.meta.get("workflow_jobs", {}).values())))
        return {
            "seed_data_dir": stores.meta.get("seed_data_dir", ""),
            "seed_modules": list(stores.meta.get("seed_modules", [])),
            "source_modules": list(stores.meta.get("source_modules", [])),
            "source_data_loaded": bool(stores.meta.get("source_data_loaded", stores.meta.get("seed_data_loaded", False))),
            "source_integrations": list(stores.meta.get("source_integrations", [])),
            "available_payloads": dict(stores.meta.get("seed_platform_payloads", {})),
            "request_samples": list(request_samples),
            "identity_count": identity_count,
            "assessment_count": len(stores.item_bank),
            "assessment_ids": sorted(stores.item_bank.keys()),
            "workflow_job_count": len(workflow_jobs),
            "latest_workflow_job": workflow_jobs[0] if workflow_jobs else None,
        }

    # Block comment:
    # Read routes query multiple containers and aggregate payload.
    def execute(
        self,
        stores: PlatformStores,
        path: str,
        payload: dict[str, object],
        identity_mapper: object,
        core_intelligence: object,
        activation_services: object,
        assessments: object,
        analytics: object,
        context: RequestContext | None = None,
    ) -> dict[str, object]:
        """Execute query route and return response body data."""
        # Line comment: route by path prefix to appropriate read operations.
        if path.startswith("/identity"):
            employee_id = self._resolve_target_employee_id(payload, context)
            self._authorize_employee_access(employee_id, context)
            canonical = identity_mapper.read_identity(employee_id)
            return {"identity": canonical}
        if path.startswith("/skills"):
            employee_id = self._resolve_target_employee_id(payload, context)
            self._authorize_employee_access(employee_id, context)
            states = core_intelligence.read_skill_states(employee_id)
            return {"skills": states}
        if path.startswith("/coaching"):
            employee_id = self._resolve_target_employee_id(payload, context)
            self._authorize_employee_access(employee_id, context)
            plan = activation_services.get_coaching_recommendations(employee_id)
            return {"coaching": plan}
        if path.startswith("/mobility"):
            employee_id = self._resolve_target_employee_id(payload, context)
            self._authorize_employee_access(employee_id, context)
            plan = activation_services.get_coaching_recommendations(employee_id)
            return {"mobility": plan}
        if path.startswith("/assessments"):
            result: dict[str, object] = {}
            if "employee_id" in payload:
                # Line comment: enforce optional employee hints used by manager/admin assessment lookups.
                self._authorize_employee_access(str(payload["employee_id"]), context)
            # Line comment: return package metadata when the caller provides an assessment id.
            if "assessment_id" in payload:
                result["assessment"] = assessments.read_package(str(payload["assessment_id"]))
            # Line comment: return attempt state when the caller provides an attempt id.
            if "attempt_id" in payload:
                attempt_payload = assessments.read_attempt(str(payload["attempt_id"]))
                if isinstance(attempt_payload, dict):
                    session_payload = attempt_payload.get("session", {})
                    if isinstance(session_payload, dict) and session_payload.get("employee_id"):
                        # Line comment: enforce cross-user access policy when attempts contain employee ownership.
                        self._authorize_employee_access(str(session_payload["employee_id"]), context)
                result["assessment_attempt"] = attempt_payload
            return result if result else {"message": "No assessment identifier provided."}
        if path.startswith("/analytics"):
            result = analytics.analytics_query(payload)
            return {"analytics": result}
        if path.startswith("/workflows"):
            # Line comment: return one workflow job when the caller asks for a specific identifier.
            if "job_id" in payload:
                return {"workflow_job": analytics.get_workflow_job(str(payload["job_id"]))}
            # Line comment: otherwise return a newest-first workflow job listing.
            return {"workflow_jobs": analytics.list_workflow_jobs(int(payload.get("limit", 20)))}
        if path.startswith("/governance"):
            return {"governance": self._build_governance_summary(stores)}
        if path.startswith("/admin"):
            return {"admin": self._build_admin_summary(stores)}
        # Line comment: return empty dataset when route is unknown.
        return {"message": "No query route matched."}


@dataclass
class CommandOrchestrator:
    """Handles write/action path orchestration to downstream APIs."""

    # Block comment:
    # This helper resolves whether one actor can execute privileged command routes.
    def _is_privileged_actor(self, context: RequestContext | None) -> bool:
        """Return whether one actor context can execute privileged commands."""
        # Line comment: allow command calls without context to preserve legacy direct unit coverage paths.
        if context is None:
            return True
        return any(role in {"manager", "admin"} for role in context.roles)

    # Block comment:
    # This helper resolves a command employee target from payload or current actor context.
    def _resolve_target_employee_id(self, payload: dict[str, object], context: RequestContext | None) -> str:
        """Resolve one employee id target for user-scoped command routes."""
        # Line comment: prefer explicit payload employee ids before context defaults.
        if "employee_id" in payload:
            return str(payload["employee_id"])
        if context is not None and context.actor_id:
            # Line comment: default to authenticated actor for self-scoped commands.
            return str(context.actor_id)
        raise ValueError("employee_id is required for this command.")

    # Block comment:
    # This helper authorizes mutating operations against one employee's records.
    def _authorize_employee_access(self, employee_id: str, context: RequestContext | None) -> None:
        """Authorize one actor context for one command employee target."""
        # Line comment: preserve permissive behavior for legacy direct command invocations without context.
        if context is None:
            return
        if employee_id == context.actor_id:
            return
        if self._is_privileged_actor(context):
            return
        raise PermissionError("Actor cannot mutate records for another employee.")

    # Block comment:
    # Command routes trigger state changes across containers.
    def execute(
        self,
        path: str,
        payload: dict[str, object],
        identity_mapper: object,
        core_intelligence: object,
        activation_services: object,
        assessments: object,
        analytics: object,
        context: RequestContext | None = None,
    ) -> dict[str, object]:
        """Execute command route and return command results."""
        # Line comment: route identity linking commands.
        if path.startswith("/command/identity/link"):
            if not self._is_privileged_actor(context):
                raise PermissionError("Identity linking requires manager or admin role.")
            result = identity_mapper.link_identity(
                str(payload["external_id"]),
                str(payload["employee_id"]),
            )
            return {"identity_linked": result}
        # Line comment: route inference command for evidence ingestion.
        if path.startswith("/command/core/infer"):
            employee_id = self._resolve_target_employee_id(payload, context)
            self._authorize_employee_access(employee_id, context)
            normalized_payload = dict(payload)
            normalized_payload["employee_id"] = employee_id
            state = core_intelligence.ingest_evidence(normalized_payload)
            return {"skill_state": state.__dict__}
        # Line comment: route activation command.
        if path.startswith("/command/activation/coaching"):
            employee_id = self._resolve_target_employee_id(payload, context)
            self._authorize_employee_access(employee_id, context)
            plan = activation_services.create_coaching_action(
                employee_id,
                str(payload.get("goal_skill", "general")),
            )
            return {"coaching_action": plan}
        # Line comment: route assessments submission command.
        if path.startswith("/command/assessments/submit"):
            employee_id = self._resolve_target_employee_id(payload, context)
            self._authorize_employee_access(employee_id, context)
            normalized_payload = dict(payload)
            normalized_payload["employee_id"] = employee_id
            result = assessments.submit_assessment(normalized_payload)
            return {"assessment_result": result}
        # Line comment: route analytics materialization command.
        if path.startswith("/command/analytics/materialize"):
            if context is not None and not self._is_privileged_actor(context):
                raise PermissionError("Analytics materialization requires manager or admin role.")
            run = analytics.trigger_materialization(
                str(payload.get("trigger", "manual")),
                bool(payload.get("wait_for_completion", True)),
            )
            return {"materialization_run": run}
        # Line comment: no-op for unknown command route.
        return {"message": "No command route matched."}


@dataclass
class RequestRouter:
    """Routes requests between query and command paths."""

    query: QueryComposer
    command: CommandOrchestrator

    # Block comment:
    # Command routes are detected by explicit /command prefix.
    def route(
        self,
        request: PlatformRequest,
        stores: PlatformStores,
        identity_mapper: object,
        core_intelligence: object,
        activation_services: object,
        assessments: object,
        analytics: object,
        context: RequestContext | None = None,
    ) -> dict[str, object]:
        """Route request and execute corresponding composer/orchestrator."""
        # Line comment: execute command route for mutating requests.
        if request.path.startswith("/command"):
            return self.command.execute(
                request.path,
                request.payload,
                identity_mapper,
                core_intelligence,
                activation_services,
                assessments,
                analytics,
                context=context,
            )
        # Line comment: execute query route for read requests.
        return self.query.execute(
            stores,
            request.path,
            request.payload,
            identity_mapper,
            core_intelligence,
            activation_services,
            assessments,
            analytics,
            context=context,
        )


@dataclass
class ResponseComposer:
    """Composes standardized response envelope."""

    # Block comment:
    # Response composition normalizes status and body fields.
    def compose(self, body: dict[str, object], status_code: int = 200) -> dict[str, object]:
        """Compose standardized body payload."""
        # Line comment: return normalized envelope body.
        return {"status": "ok" if status_code < 400 else "error", "data": body}


@dataclass
class AuditHook:
    """Writes audit records for response envelopes."""

    stores: PlatformStores

    # Block comment:
    # Every gateway response gets a corresponding audit id.
    def write(self, actor_id: str, path: str, response_body: dict[str, object]) -> str:
        """Persist audit envelope and return audit identifier."""
        # Line comment: create unique audit id for this response.
        audit_id = f"audit-{uuid4().hex[:12]}"
        self.stores.append(
            "audit",
            {
                "audit_id": audit_id,
                "actor_id": actor_id,
                "path": path,
                "response": response_body,
                "event_type": "GatewayResponse",
            },
        )
        return audit_id


@dataclass
class FederationGateway:
    """Composed federation gateway implementing the Level 3A flow."""

    stores: PlatformStores
    identity_mapper: object
    core_intelligence: object
    activation_services: object
    assessments: object
    analytics: object
    api: WebAPIEntry = field(init=False)
    rate: RateLimiter = field(init=False)
    auth: AuthAdapter = field(init=False)
    tenant: TenantResolver = field(init=False)
    flags: FeatureFlagEvaluator = field(init=False)
    ctx_builder: SessionContextBuilder = field(init=False)
    query: QueryComposer = field(init=False)
    command: CommandOrchestrator = field(init=False)
    router: RequestRouter = field(init=False)
    response: ResponseComposer = field(init=False)
    audit: AuditHook = field(init=False)

    def __post_init__(self) -> None:
        """Initialize all gateway components."""
        # Line comment: instantiate each Level 3A component.
        self.api = WebAPIEntry()
        self.rate = RateLimiter(self.stores)
        self.auth = AuthAdapter(self.stores)
        self.tenant = TenantResolver()
        self.flags = FeatureFlagEvaluator(self.stores)
        self.ctx_builder = SessionContextBuilder()
        self.query = QueryComposer()
        self.command = CommandOrchestrator()
        self.router = RequestRouter(self.query, self.command)
        self.response = ResponseComposer()
        self.audit = AuditHook(self.stores)

    # Block comment:
    # This method executes the full request pipeline in diagram order.
    def handle(self, request: PlatformRequest) -> PlatformResponse:
        """Handle one request through the complete gateway flow."""
        # Line comment: enter at web/api boundary.
        inbound = self.api.accept(request)
        # Line comment: apply actor-level throttling.
        self.rate.throttle(inbound.actor_id)
        # Line comment: authenticate and resolve claims.
        claims = self.auth.authenticate(inbound.token, inbound.actor_id)
        authenticated_actor_id = str(claims.get("actor_id", claims.get("sub", inbound.actor_id)))
        if not authenticated_actor_id:
            raise PermissionError("Unable to resolve authenticated actor.")
        if authenticated_actor_id != inbound.actor_id:
            # Line comment: throttle canonical actor ids when inbound aliases differ from auth subject.
            self.rate.throttle(authenticated_actor_id)
        # Line comment: derive tenant and feature flags.
        tenant_id = self.tenant.resolve(claims)
        flags = self.flags.evaluate(tenant_id)
        # Line comment: build downstream request context using identity mapper current-context pattern.
        mapped_context = self.identity_mapper.resolve_context(authenticated_actor_id, flags)
        merged_roles = list(mapped_context.roles) if mapped_context.roles else list(claims.get("roles", ["employee"]))
        context = RequestContext(
            actor_id=authenticated_actor_id,
            tenant_id=mapped_context.tenant_id if mapped_context.tenant_id else tenant_id,
            roles=merged_roles,
            claims={**dict(mapped_context.claims), **dict(claims)},
            feature_flags=dict(flags),
        )
        normalized_request = PlatformRequest(
            method=inbound.method,
            path=inbound.path,
            actor_id=authenticated_actor_id,
            token=inbound.token,
            payload=dict(inbound.payload),
        )
        # Line comment: route to query or command handlers.
        result = self.router.route(
            normalized_request,
            self.stores,
            self.identity_mapper,
            self.core_intelligence,
            self.activation_services,
            self.assessments,
            self.analytics,
            context=context,
        )
        # Line comment: compose response and add audit trail.
        body = self.response.compose(result, status_code=200)
        audit_id = self.audit.write(authenticated_actor_id, normalized_request.path, body)
        return PlatformResponse(status_code=200, body=body, audit_id=audit_id)


@dataclass
class FederationGatewayContainer:
    """Container wrapper exposing request handling for platform composition."""

    identity_mapper_api: Any
    core_intelligence_api: Any
    activation_services_api: Any
    assessments_api: Any
    analytics_api: Any
    stores: PlatformStores
    _gateway: FederationGateway = field(init=False)

    def __post_init__(self) -> None:
        """Build the composed federation gateway implementation."""
        # Block comment:
        # The wrapper adapts platform composition naming to gateway class naming.
        # Line comment: instantiate the composed gateway with container APIs.
        self._gateway = FederationGateway(
            stores=self.stores,
            identity_mapper=self.identity_mapper_api,
            core_intelligence=self.core_intelligence_api,
            activation_services=self.activation_services_api,
            assessments=self.assessments_api,
            analytics=self.analytics_api,
        )

    # Block comment:
    # This method is the canonical platform entry point for request handling.
    def handle_request(self, request: PlatformRequest) -> PlatformResponse:
        """Handle one incoming platform request through the full gateway flow."""
        # Line comment: delegate handling to the composed gateway implementation.
        return self._gateway.handle(request)

    # Block comment:
    # This alias keeps compatibility with callers expecting a handle method.
    def handle(self, request: PlatformRequest) -> PlatformResponse:
        """Handle one incoming request with the composed gateway."""
        # Line comment: delegate to the same implementation as handle_request.
        return self.handle_request(request)
