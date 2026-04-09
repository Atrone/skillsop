"""Platform composition root wiring architecture containers together."""

from __future__ import annotations

from skillsai.containers.activation_services import ActivationServicesAPI
from skillsai.containers.analytics_longitudinal import AnalyticsLongitudinalContainer
from skillsai.containers.assessments import SkillsAIAssessmentsContainer
from skillsai.containers.core_intelligence import CoreIntelligenceContainer
from skillsai.containers.federation_gateway import FederationGatewayContainer
from skillsai.containers.identity_mapper import IdentityMapperAPI
from skillsai.event_bus import EventBus
from skillsai.stores import PlatformStores


class SkillsAIPlatform:
    """Bootstraps Option 17 architecture into executable Python objects."""

    # Block comment:
    # The initializer composes all containers and attaches event subscriptions.
    def __init__(self) -> None:
        """Initialize stores, bus, and all architecture containers."""
        # Line comment: create shared infrastructure used by all containers.
        self.stores = PlatformStores()
        self.event_bus = EventBus()

        # Line comment: instantiate each container in the dependency order from Level 2.
        self.identity_mapper = IdentityMapperAPI(stores=self.stores)
        self.core_intelligence = CoreIntelligenceContainer(
            stores=self.stores,
            event_bus=self.event_bus,
        )
        self.activation_services = ActivationServicesAPI(stores=self.stores, event_bus=self.event_bus)
        self.assessments = SkillsAIAssessmentsContainer(
            stores=self.stores,
            core_api=self.core_intelligence,
            event_bus=self.event_bus,
        )
        self.analytics = AnalyticsLongitudinalContainer(stores=self.stores, event_bus=self.event_bus)
        self.gateway = FederationGatewayContainer(
            identity_mapper_api=self.identity_mapper,
            core_intelligence_api=self.core_intelligence,
            activation_services_api=self.activation_services,
            assessments_api=self.assessments,
            analytics_api=self.analytics,
            stores=self.stores,
        )
        # Line comment: preserve alternate names used by existing callers.
        self.federation_gateway = self.gateway
        self.bus = self.event_bus
        # Line comment: register event-bus triggers and projections.
        self._register_event_subscriptions()

    # Block comment:
    # This method wires asynchronous architecture flows defined in Level 2.
    def _register_event_subscriptions(self) -> None:
        """Subscribe analytics refresh handlers to platform events."""
        # Line comment: all known event names trigger analytics refresh scheduling.
        self.event_bus.subscribe("SkillStateUpdated", self.analytics.handle_bus_event)
        self.event_bus.subscribe("AssessmentEvidencePublished", self.analytics.handle_bus_event)
        self.event_bus.subscribe("MobilityRecommendationCreated", self.analytics.handle_bus_event)

