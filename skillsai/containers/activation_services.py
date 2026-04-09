"""Activation Services container implementation for coaching and mobility."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from skillsai.event_bus import PlatformEventBus
from skillsai.models import RequestContext
from skillsai.stores import PlatformStores


@dataclass(slots=True)
class ActivationServicesAPI:
    """Serves coaching and mobility reads/actions for the gateway."""

    stores: PlatformStores
    event_bus: PlatformEventBus

    # Block comment:
    # This read path mirrors query composition flow for coaching and mobility.
    def read(self, context: RequestContext, request: dict[str, Any]) -> dict[str, Any]:
        """Return coaching and mobility recommendations for one employee."""
        # Line comment: locate the subject employee requested by the caller.
        employee_id = request.get("employee_id", context.actor_id)
        # Line comment: read inferred skill states from the skills graph store.
        states = self.stores.graph.get(employee_id, {}).get("skills", {})
        recommendations: list[dict[str, Any]] = []
        # Line comment: score each skill for next-best action.
        for skill_id, state in states.items():
            if state["gap"] > 0:
                recommendations.append(
                    {
                        "type": "coaching",
                        "skill_id": skill_id,
                        "priority": round(state["gap"] * state["confidence"], 4),
                    }
                )
        # Line comment: persist recommendation decision audit.
        self.stores.append(
            "audit",
            {
                "event": "activation.read",
                "tenant": context.tenant_id,
                "actor": context.actor_id,
                "employee_id": employee_id,
                "recommendation_count": len(recommendations),
            },
        )
        # Line comment: return deterministic ordered recommendations.
        recommendations.sort(key=lambda item: item["priority"], reverse=True)
        return {"employee_id": employee_id, "recommendations": recommendations}

    # Block comment:
    # This write path captures explicit user actions and updates derived metrics.
    def act(self, context: RequestContext, command: dict[str, Any]) -> dict[str, Any]:
        """Record a coaching or mobility action and update outcome metrics."""
        # Line comment: extract action details from the command envelope.
        action_type = command.get("action_type", "coaching")
        skill_id = command["skill_id"]
        outcome = command.get("outcome", "accepted")
        # Line comment: append interaction events for longitudinal tracking.
        self.stores.append(
            "time_series",
            {
                "event": "activation.action",
                "tenant": context.tenant_id,
                "actor": context.actor_id,
                "action_type": action_type,
                "skill_id": skill_id,
                "outcome": outcome,
            },
        )
        # Line comment: update simple activation outcome metric in mart.
        metric_key = f"activation:{action_type}:{outcome}"
        self.stores.mart[metric_key] = self.stores.mart.get(metric_key, 0) + 1
        # Line comment: publish action event for analytics refresh triggers.
        self.event_bus.publish("MobilityRecommendationCreated", {"metric_key": metric_key, "value": self.stores.mart[metric_key]})
        return {
            "status": "recorded",
            "metric_key": metric_key,
            "value": self.stores.mart[metric_key],
        }

    # Block comment:
    # This helper method provides gateway query-path compatibility.
    def get_coaching_recommendations(self, employee_id: str) -> dict[str, Any]:
        """Return recommendations using a synthetic request context."""
        # Line comment: construct minimal context for direct gateway query invocation.
        context = RequestContext(
            actor_id=employee_id,
            tenant_id="default-tenant",
            roles=["employee"],
            claims={},
            feature_flags={},
        )
        return self.read(context, {"employee_id": employee_id})

    # Block comment:
    # This helper method provides gateway command-path compatibility.
    def create_coaching_action(self, employee_id: str, goal_skill: str) -> dict[str, Any]:
        """Record coaching action for gateway command orchestration."""
        # Line comment: construct minimal context for direct command invocation.
        context = RequestContext(
            actor_id=employee_id,
            tenant_id="default-tenant",
            roles=["employee"],
            claims={},
            feature_flags={},
        )
        return self.act(
            context,
            {
                "action_type": "coaching",
                "skill_id": goal_skill,
                "outcome": "accepted",
            },
        )
