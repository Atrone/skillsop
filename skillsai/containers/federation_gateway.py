"""Federation gateway container and components (C4 Level 3A)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from skillsai.models import PlatformRequest, PlatformResponse, RequestContext
from skillsai.stores import PlatformStores


@dataclass(slots=True)
class WebAPIEntry:
    """Receives inbound user/API requests."""

    # Block comment:
    # This component is the entry adapter and can normalize inputs.
    def accept(self, request: PlatformRequest) -> PlatformRequest:
        """Accept and return the inbound request unchanged."""
        # Line comment: return request after edge acceptance.
        return request


@dataclass(slots=True)
class RateLimiter:
    """Applies simple per-actor rate limiting."""

    stores: PlatformStores
    max_requests: int = 100

    # Block comment:
    # This implementation tracks per-actor counters in cache.
    def throttle(self, actor_id: str) -> None:
        """Raise if actor has exceeded a simplistic fixed request budget."""
        # Line comment: resolve current actor request count.
        key = f"rate:{actor_id}"
        current = int(self.stores.cache.get(key, 0))
        if current >= self.max_requests:
            raise PermissionError("Rate limit exceeded.")
        # Line comment: increment count after successful check.
        self.stores.cache[key] = current + 1


@dataclass(slots=True)
class AuthAdapter:
    """Validates tokens/claims through an identity provider boundary."""

    # Block comment:
    # This method models token/claim verification from an IdP.
    def authenticate(self, token: str) -> dict[str, object]:
        """Return normalized claims for a non-empty bearer token."""
        # Line comment: reject empty tokens as unauthorized.
        if not token:
            raise PermissionError("Missing authentication token.")
        # Line comment: derive synthetic claims for demo architecture.
        parts = token.split(":")
        return {"sub": parts[0], "tenant_hint": parts[1] if len(parts) > 1 else "default"}


@dataclass(slots=True)
class TenantResolver:
    """Resolves tenant context for requests."""

    # Block comment:
    # The resolver chooses tenant from claims with a fallback.
    def resolve(self, claims: dict[str, object]) -> str:
        """Resolve tenant id from auth claims."""
        # Line comment: return explicit tenant hint or default tenant.
        tenant = claims.get("tenant_hint", "default")
        return str(tenant)


@dataclass(slots=True)
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


@dataclass(slots=True)
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


@dataclass(slots=True)
class QueryComposer:
    """Handles read path composition to downstream APIs."""

    # Block comment:
    # Read routes query multiple containers and aggregate payload.
    def execute(
        self,
        path: str,
        payload: dict[str, object],
        identity_mapper: object,
        core_intelligence: object,
        activation_services: object,
        assessments: object,
        analytics: object,
    ) -> dict[str, object]:
        """Execute query route and return response body data."""
        # Line comment: route by path prefix to appropriate read operations.
        if path.startswith("/identity"):
            canonical = identity_mapper.read_identity(str(payload["employee_id"]))
            return {"identity": canonical}
        if path.startswith("/skills"):
            states = core_intelligence.read_skill_states(str(payload["employee_id"]))
            return {"skills": states}
        if path.startswith("/coaching"):
            plan = activation_services.get_coaching_recommendations(str(payload["employee_id"]))
            return {"coaching": plan}
        if path.startswith("/assessments"):
            attempt = assessments.read_attempt(str(payload["attempt_id"]))
            return {"assessment_attempt": attempt}
        if path.startswith("/analytics"):
            result = analytics.analytics_query(payload)
            return {"analytics": result}
        # Line comment: return empty dataset when route is unknown.
        return {"message": "No query route matched."}


@dataclass(slots=True)
class CommandOrchestrator:
    """Handles write/action path orchestration to downstream APIs."""

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
    ) -> dict[str, object]:
        """Execute command route and return command results."""
        # Line comment: route identity linking commands.
        if path.startswith("/command/identity/link"):
            result = identity_mapper.link_identity(
                str(payload["external_id"]),
                str(payload["employee_id"]),
            )
            return {"identity_linked": result}
        # Line comment: route inference command for evidence ingestion.
        if path.startswith("/command/core/infer"):
            state = core_intelligence.ingest_evidence(payload)
            return {"skill_state": state.__dict__}
        # Line comment: route activation command.
        if path.startswith("/command/activation/coaching"):
            plan = activation_services.create_coaching_action(
                str(payload["employee_id"]),
                str(payload.get("goal_skill", "general")),
            )
            return {"coaching_action": plan}
        # Line comment: route assessments submission command.
        if path.startswith("/command/assessments/submit"):
            result = assessments.submit_assessment(payload)
            return {"assessment_result": result}
        # Line comment: route analytics materialization command.
        if path.startswith("/command/analytics/materialize"):
            run = analytics.trigger_materialization(str(payload.get("trigger", "manual")))
            return {"materialization_run": run}
        # Line comment: no-op for unknown command route.
        return {"message": "No command route matched."}


@dataclass(slots=True)
class RequestRouter:
    """Routes requests between query and command paths."""

    query: QueryComposer
    command: CommandOrchestrator

    # Block comment:
    # Command routes are detected by explicit /command prefix.
    def route(
        self,
        request: PlatformRequest,
        identity_mapper: object,
        core_intelligence: object,
        activation_services: object,
        assessments: object,
        analytics: object,
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
            )
        # Line comment: execute query route for read requests.
        return self.query.execute(
            request.path,
            request.payload,
            identity_mapper,
            core_intelligence,
            activation_services,
            assessments,
            analytics,
        )


@dataclass(slots=True)
class ResponseComposer:
    """Composes standardized response envelope."""

    # Block comment:
    # Response composition normalizes status and body fields.
    def compose(self, body: dict[str, object], status_code: int = 200) -> dict[str, object]:
        """Compose standardized body payload."""
        # Line comment: return normalized envelope body.
        return {"status": "ok" if status_code < 400 else "error", "data": body}


@dataclass(slots=True)
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


@dataclass(slots=True)
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
        self.auth = AuthAdapter()
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
        claims = self.auth.authenticate(inbound.token)
        # Line comment: derive tenant and feature flags.
        tenant_id = self.tenant.resolve(claims)
        flags = self.flags.evaluate(tenant_id)
        # Line comment: build downstream request context (not persisted).
        _context = self.ctx_builder.build(inbound.actor_id, tenant_id, claims, flags)
        # Line comment: route to query or command handlers.
        result = self.router.route(
            inbound,
            self.identity_mapper,
            self.core_intelligence,
            self.activation_services,
            self.assessments,
            self.analytics,
        )
        # Line comment: compose response and add audit trail.
        body = self.response.compose(result, status_code=200)
        audit_id = self.audit.write(inbound.actor_id, inbound.path, body)
        return PlatformResponse(status_code=200, body=body, audit_id=audit_id)


@dataclass(slots=True)
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
