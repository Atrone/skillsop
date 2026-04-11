"""Activation Services container implementation for coaching and mobility."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    from ..event_bus import PlatformEventBus
    from ..models import RequestContext
    from ..stores import PlatformStores
except ImportError:
    from event_bus import PlatformEventBus
    from models import RequestContext
    from stores import PlatformStores


@dataclass
class ActivationServicesAPI:
    """Serves coaching and mobility reads/actions for the gateway."""

    stores: PlatformStores
    event_bus: PlatformEventBus

    # Block comment:
    # This helper derives recommendations from either nested or flat graph store shapes.
    def _build_graph_recommendations(self, employee_id: str) -> list[dict[str, Any]]:
        """Build coaching recommendations from graph-backed skill states."""
        # Line comment: accumulate one recommendation per skill id to avoid duplicates across store layouts.
        recommendations_by_skill: dict[str, dict[str, Any]] = {}
        nested_state = self.stores.graph.get(employee_id, {})
        nested_skills = nested_state.get("skills", {}) if isinstance(nested_state, dict) else {}
        for skill_id, state in nested_skills.items():
            # Line comment: compute one recommendation from nested employee->skills records.
            gap = float(state.get("gap", 0.0))
            confidence = float(state.get("confidence", 0.0))
            if gap > 0:
                recommendations_by_skill[str(skill_id)] = {
                    "type": "coaching",
                    "skill_id": str(skill_id),
                    "priority": round(gap * max(confidence, 0.0), 4),
                }
        for key, state in self.stores.graph.items():
            # Line comment: also support the flat employee_id:skill_id graph layout used by core intelligence.
            if not key.startswith(f"{employee_id}:") or not isinstance(state, dict):
                continue
            skill_id = str(state.get("skill_id", key.split(":", 1)[1]))
            gap = float(state.get("gap", 0.0))
            confidence = float(state.get("confidence", 0.0))
            if gap > 0:
                recommendations_by_skill[skill_id] = {
                    "type": "coaching",
                    "skill_id": skill_id,
                    "priority": round(gap * max(confidence, 0.0), 4),
                }
        # Line comment: return a stable priority-sorted recommendation list for UI consumers.
        recommendations = list(recommendations_by_skill.values())
        recommendations.sort(key=lambda item: item["priority"], reverse=True)
        return recommendations

    # Block comment:
    # This read path mirrors query composition flow for coaching and mobility.
    def read(self, context: RequestContext, request: dict[str, Any]) -> dict[str, Any]:
        """Return coaching and mobility recommendations for one employee."""
        # Line comment: locate the subject employee requested by the caller.
        employee_id = request.get("employee_id", context.actor_id)
        # Line comment: prefer explicit seed-data recommendations when they are available.
        seeded_recommendations = self.stores.cache.get(f"activation:{employee_id}", {})
        if isinstance(seeded_recommendations, dict) and isinstance(seeded_recommendations.get("recommendations"), list):
            recommendations = list(seeded_recommendations["recommendations"])
        else:
            # Line comment: derive fallback recommendations from graph-backed skill states.
            recommendations = self._build_graph_recommendations(str(employee_id))
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
