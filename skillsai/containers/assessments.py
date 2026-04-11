"""SkillsAI Assessments container implementation (Level 3C)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from skillsai.event_bus import PlatformEventBus
from skillsai.models import AssessmentSubmission, EvidenceSignal
from skillsai.stores import PlatformStores


class AuthoringUIAPI:
    """Authoring UI/API component."""

    # Block comment:
    # This method stores draft authoring artifacts before publication.
    def author(self, stores: PlatformStores, assessment_id: str, definition: dict[str, Any]) -> None:
        """Persist authored content for one assessment definition."""
        # Line comment: keep the latest draft in metadata for version workflow.
        stores.meta[f"assessment:draft:{assessment_id}"] = definition


class BlueprintDesigner:
    """Blueprint Designer component."""

    # Block comment:
    # This method derives a simple blueprint map from authored sections.
    def design(self, definition: dict[str, Any]) -> dict[str, Any]:
        """Build blueprint content from authored definitions."""
        # Line comment: copy key structural fields for publication packaging.
        return {"sections": definition.get("sections", []), "duration_min": definition.get("duration_min", 30)}


class ItemAuthoringStudio:
    """Item Authoring Studio component."""

    # Block comment:
    # This method extracts item definitions from authored assessment payload.
    def create_items(self, definition: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract item payloads from definition."""
        # Line comment: normalize to list shape expected by item bank publisher.
        return list(definition.get("items", []))


class RubricEditor:
    """Rubric Editor component."""

    # Block comment:
    # This method extracts rubric logic for scoring pipeline consumption.
    def build_rubric(self, definition: dict[str, Any]) -> dict[str, Any]:
        """Build rubric payload from authored definition."""
        # Line comment: default to objective weighting when not explicitly specified.
        return definition.get("rubric", {"weights": {"objective": 1.0}})


class VersionPublishWorkflow:
    """Version & Publish Workflow component."""

    # Block comment:
    # This method persists a publishable form package into item bank and metadata.
    def publish(
        self,
        stores: PlatformStores,
        assessment_id: str,
        blueprint: dict[str, Any],
        items: list[dict[str, Any]],
        rubric: dict[str, Any],
    ) -> dict[str, Any]:
        """Publish assessment package to item bank and metadata stores."""
        # Line comment: increment a simple version counter in metadata.
        version = int(stores.meta.get(f"assessment:version:{assessment_id}", 0)) + 1
        package = {"assessment_id": assessment_id, "version": version, "blueprint": blueprint, "items": items, "rubric": rubric}
        # Line comment: write publish package to the Assessment Item Bank store.
        stores.item_bank[assessment_id] = package
        # Line comment: store version lineage in metadata.
        stores.meta[f"assessment:version:{assessment_id}"] = version
        stores.meta[f"assessment:published:{assessment_id}:v{version}"] = package
        return package


class DeliveryUIAPI:
    """Delivery UI/API component."""

    # Block comment:
    # This method returns assignment-ready metadata for a learner session.
    def start(self, assessment_id: str, employee_id: str) -> dict[str, str]:
        """Initialize delivery request context."""
        # Line comment: package identifiers for assignment resolver.
        return {"assessment_id": assessment_id, "employee_id": employee_id}


class AssignmentResolver:
    """Assignment Resolver component."""

    # Block comment:
    # This method resolves a concrete form package for an employee.
    def resolve(self, stores: PlatformStores, request: dict[str, str]) -> dict[str, Any]:
        """Resolve assessment package from item bank."""
        # Line comment: return the published package by assessment id.
        return stores.item_bank[request["assessment_id"]]


class SessionManager:
    """Session Manager component."""

    # Block comment:
    # This method opens and persists an attempt session in attempts store.
    def open_session(self, stores: PlatformStores, form: dict[str, Any], employee_id: str, attempt_id: str) -> dict[str, Any]:
        """Create one active assessment session."""
        # Line comment: initialize attempt status before rendering.
        session = {"attempt_id": attempt_id, "employee_id": employee_id, "assessment_id": form["assessment_id"], "status": "open"}
        stores.attempts[attempt_id] = {"session": session, "responses": {}, "scores": {}}
        return session


class FormRenderer:
    """Form Renderer component."""

    # Block comment:
    # This method projects form content used by front-end delivery clients.
    def render(self, form: dict[str, Any]) -> dict[str, Any]:
        """Render display payload for one form."""
        # Line comment: include items and rubric summary for the session.
        return {"assessment_id": form["assessment_id"], "items": form["items"], "rubric": form["rubric"]}


class ResponseCapture:
    """Response Capture component."""

    # Block comment:
    # This method saves interim or final responses to attempts store.
    def capture(self, stores: PlatformStores, attempt_id: str, responses: dict[str, Any]) -> None:
        """Persist captured responses for one attempt."""
        # Line comment: write response payload under attempt record.
        stores.attempts[attempt_id]["responses"] = dict(responses)


class SubmissionManager:
    """Submission Manager component."""

    # Block comment:
    # This method marks attempt submitted and emits audit/session records.
    def submit(self, stores: PlatformStores, submission: AssessmentSubmission) -> None:
        """Finalize an attempt and append submission audit event."""
        # Line comment: set terminal attempt status for scoring intake.
        stores.attempts[submission.attempt_id]["session"]["status"] = "submitted"
        # Line comment: append consent/session audit entry.
        stores.audit.append({"event": "assessment_submitted", "attempt_id": submission.attempt_id, "employee_id": submission.employee_id})


class ScoringIntake:
    """Scoring Intake component."""

    # Block comment:
    # This method fan-outs submission payload to objective and rubric scorers.
    def intake(self, submission: AssessmentSubmission) -> dict[str, Any]:
        """Prepare scoring payload from submission."""
        # Line comment: preserve response payload exactly for downstream scorers.
        return {"responses": submission.responses, "attempt_id": submission.attempt_id}


class ObjectiveScorer:
    """Objective Scorer component."""

    # Block comment:
    # This method scores objective responses using exact-match semantics.
    def score(self, payload: dict[str, Any]) -> float:
        """Compute objective score ratio."""
        # Line comment: treat boolean true answers as correct items.
        responses = payload["responses"]
        if not responses:
            return 0.0
        correct = sum(1 for _k, v in responses.items() if v is True)
        return round(correct / len(responses), 4)


class RubricScorer:
    """Rubric Scorer component."""

    # Block comment:
    # This method applies simplistic rubric score extraction from numeric answers.
    def score(self, payload: dict[str, Any]) -> float:
        """Compute rubric score ratio from numeric entries."""
        # Line comment: use integer/float response values as rubric judgments.
        numeric = [float(v) for v in payload["responses"].values() if isinstance(v, (int, float))]
        if not numeric:
            return 0.0
        # Line comment: normalize on an assumed 5-point rubric scale.
        return round((sum(numeric) / len(numeric)) / 5.0, 4)


class CalibrationReliability:
    """Calibration / Reliability component."""

    # Block comment:
    # This method returns a reliability factor used by score normalization.
    def calibrate(self, objective_score: float, rubric_score: float) -> float:
        """Compute reliability factor from scorer agreement."""
        # Line comment: lower disagreement yields higher reliability.
        delta = abs(objective_score - rubric_score)
        return round(max(0.5, 1.0 - delta), 4)


class ScoreNormalizer:
    """Score Normalizer component."""

    # Block comment:
    # This method combines scorer outputs into one final normalized score.
    def normalize(self, objective_score: float, rubric_score: float, reliability: float) -> float:
        """Normalize final score using weighted average and reliability."""
        # Line comment: blend objective and rubric scores evenly.
        blended = (objective_score + rubric_score) / 2.0
        # Line comment: apply reliability as multiplicative adjustment.
        return round(blended * reliability, 4)


class ScoringPublisher:
    """Scoring Publisher component."""

    # Block comment:
    # This method persists final scores and emits scoring audit records.
    def publish(self, stores: PlatformStores, attempt_id: str, final_score: float) -> None:
        """Persist score and append scoring audit event."""
        # Line comment: write final score in attempts store.
        stores.attempts[attempt_id]["scores"]["final"] = final_score
        # Line comment: append audit entry for score publication.
        stores.audit.append({"event": "assessment_scored", "attempt_id": attempt_id, "score": final_score})


class EvidenceMapper:
    """Evidence Mapper component."""

    # Block comment:
    # This method maps assessment outcomes to one or more skill ids.
    def map(self, assessment_id: str, final_score: float) -> list[dict[str, Any]]:
        """Map score output into skill-targeted evidence records."""
        # Line comment: derive stable pseudo skill id from assessment id.
        skill_id = f"skill:{assessment_id}"
        return [{"skill_id": skill_id, "score": final_score}]


class SkillSignalTranslator:
    """Skill Signal Translator component."""

    # Block comment:
    # This method converts mapped evidence into inference-ready signal objects.
    def translate(self, employee_id: str, mapped: list[dict[str, Any]]) -> list[EvidenceSignal]:
        """Translate mapped assessment evidence to inference signals."""
        signals: list[EvidenceSignal] = []
        # Line comment: create one signal per mapped skill record.
        for record in mapped:
            signals.append(
                EvidenceSignal(
                    employee_id=employee_id,
                    skill_id=record["skill_id"],
                    value=float(record["score"]),
                    source="assessment",
                    confidence_hint=0.8,
                    metadata={"evidence_type": "assessment_score"},
                )
            )
        return signals


class OutcomeEventBuilder:
    """Outcome Event Builder component."""

    # Block comment:
    # This method builds durable event records from inference-ready signals.
    def build(self, attempt_id: str, signals: list[EvidenceSignal]) -> list[dict[str, Any]]:
        """Build event payloads for event store and KPI update flow."""
        events: list[dict[str, Any]] = []
        # Line comment: emit one event per signal to preserve granularity.
        for signal in signals:
            events.append(
                {
                    "event": "assessment_evidence",
                    "attempt_id": attempt_id,
                    "employee_id": signal.employee_id,
                    "skill_id": signal.skill_id,
                    "value": signal.value,
                }
            )
        return events


class MetricsUpdater:
    """Metrics Updater component."""

    # Block comment:
    # This method updates derived KPI values based on assessment events.
    def update(self, stores: PlatformStores, events: list[dict[str, Any]]) -> None:
        """Update assessment KPI counters in mart store."""
        # Line comment: increment published evidence count metric.
        stores.mart["assessment_evidence_events"] = int(stores.mart.get("assessment_evidence_events", 0)) + len(events)


class InferenceFeedPublisher:
    """Inference Feed Publisher component."""

    # Block comment:
    # This method forwards translated signals into Core Intelligence ingestion.
    def publish(self, core_api: Any, signals: list[EvidenceSignal]) -> list[dict[str, Any]]:
        """Submit translated signals to core intelligence inference intake."""
        outputs: list[dict[str, Any]] = []
        # Line comment: call core inference API once per signal.
        for signal in signals:
            outputs.append(core_api.ingest_evidence(signal))
        return outputs


class SkillsAIAssessments:
    """Container façade for SkillsAI Assessments APIs and flows."""

    def __init__(self, stores: PlatformStores, bus: PlatformEventBus) -> None:
        # Line comment: keep shared store and bus references for all component flows.
        self._stores = stores
        self._bus = bus
        self._authoring = AuthoringUIAPI()
        self._blueprint = BlueprintDesigner()
        self._item_studio = ItemAuthoringStudio()
        self._rubric_editor = RubricEditor()
        self._publisher = VersionPublishWorkflow()
        self._delivery = DeliveryUIAPI()
        self._assign = AssignmentResolver()
        self._session = SessionManager()
        self._render = FormRenderer()
        self._capture = ResponseCapture()
        self._submit = SubmissionManager()
        self._s_intake = ScoringIntake()
        self._objective = ObjectiveScorer()
        self._rubric = RubricScorer()
        self._cal = CalibrationReliability()
        self._norm = ScoreNormalizer()
        self._s_pub = ScoringPublisher()
        self._map = EvidenceMapper()
        self._translate = SkillSignalTranslator()
        self._events = OutcomeEventBuilder()
        self._mupd = MetricsUpdater()
        self._ifp = InferenceFeedPublisher()

    # Block comment:
    # This method implements the Level 3C authoring publication flow.
    def publish_assessment(self, assessment_id: str, definition: dict[str, Any]) -> dict[str, Any]:
        """Author and publish assessment artifacts."""
        # Line comment: persist authored draft in metadata.
        self._authoring.author(self._stores, assessment_id, definition)
        # Line comment: derive blueprint, item set, and rubric package.
        blueprint = self._blueprint.design(definition)
        items = self._item_studio.create_items(definition)
        rubric = self._rubric_editor.build_rubric(definition)
        # Line comment: publish package to item bank and versioned metadata.
        return self._publisher.publish(self._stores, assessment_id, blueprint, items, rubric)

    # Block comment:
    # This method implements delivery through submission and final score publication.
    def submit_assessment(self, submission: AssessmentSubmission) -> float:
        """Deliver, capture, submit, and score one assessment attempt."""
        # Line comment: initialize delivery path and session for the attempt.
        request = self._delivery.start(submission.assessment_id, submission.employee_id)
        form = self._assign.resolve(self._stores, request)
        self._session.open_session(self._stores, form, submission.employee_id, submission.attempt_id)
        self._render.render(form)
        self._capture.capture(self._stores, submission.attempt_id, submission.responses)
        self._submit.submit(self._stores, submission)
        # Line comment: run scoring engine pipeline for submitted payload.
        payload = self._s_intake.intake(submission)
        objective_score = self._objective.score(payload)
        rubric_score = self._rubric.score(payload)
        reliability = self._cal.calibrate(objective_score, rubric_score)
        final_score = self._norm.normalize(objective_score, rubric_score, reliability)
        self._s_pub.publish(self._stores, submission.attempt_id, final_score)
        return final_score

    # Block comment:
    # This method implements evidence publishing from assessment outputs.
    def publish_evidence(self, core_api: Any, submission: AssessmentSubmission) -> list[dict[str, Any]]:
        """Map scored outcomes into events, KPIs, and core inference feed."""
        # Line comment: read final score from persisted attempts record.
        final_score = float(self._stores.attempts[submission.attempt_id]["scores"]["final"])
        mapped = self._map.map(submission.assessment_id, final_score)
        signals = self._translate.translate(submission.employee_id, mapped)
        events = self._events.build(submission.attempt_id, signals)
        # Line comment: append assessment events to time-series store.
        for event in events:
            self._stores.time_series.append(event)
        # Line comment: update derived KPI store from published events.
        self._mupd.update(self._stores, events)
        # Line comment: forward signals into core intelligence inference service.
        outputs = self._ifp.publish(core_api, signals)
        # Line comment: publish event bus notification for downstream refresh.
        self._bus.publish("AssessmentEvidencePublished", {"attempt_id": submission.attempt_id, "employee_id": submission.employee_id})
        return outputs


@dataclass
class SkillsAIAssessmentsContainer:
    """Container façade exposing gateway-friendly assessment APIs."""

    stores: PlatformStores
    core_api: Any
    event_bus: PlatformEventBus
    _impl: SkillsAIAssessments = field(init=False)

    def __post_init__(self) -> None:
        """Initialize internal assessment component graph."""
        # Block comment:
        # The internal pipeline class provides the detailed Level 3C component flow.
        # Line comment: create the composed assessments service implementation.
        self._impl = SkillsAIAssessments(stores=self.stores, bus=self.event_bus)

    # Block comment:
    # This method supports authoring and publication commands from admin clients.
    def publish_assessment(
        self,
        assessment_id: str,
        definition: dict[str, Any] | None = None,
        blueprint: dict[str, Any] | None = None,
        items: dict[str, dict[str, Any]] | None = None,
        rubric: dict[str, Any] | None = None,
        version: str = "v1",
    ) -> dict[str, Any]:
        """Publish one assessment package into the item bank."""
        # Block comment:
        # This method accepts either a pre-built definition or expanded authoring fields.
        # Line comment: directly pass through when normalized definition is provided.
        if definition is not None:
            return self._impl.publish_assessment(assessment_id, definition)
        # Line comment: normalize expanded arguments into the internal definition shape.
        effective_blueprint = blueprint or {"overview": "default"}
        effective_items = items or {}
        effective_rubric = rubric or {"type": "objective"}
        normalized = {
            "sections": list(effective_blueprint.keys()),
            "duration_min": 30,
            "items": [{"item_id": key, **value} for key, value in effective_items.items()],
            "rubric": effective_rubric,
            "version": version,
            "blueprint": effective_blueprint,
        }
        return self._impl.publish_assessment(assessment_id, normalized)

    # Block comment:
    # This method supports read/query path for assessment attempts.
    def read_attempt(self, attempt_id: str) -> dict[str, Any]:
        """Return persisted attempt payload by identifier."""
        # Line comment: read one attempt record from attempts store.
        return dict(self.stores.attempts.get(attempt_id, {}))

    # Block comment:
    # This method supports read/query path for published assessment package metadata.
    def read_package(self, assessment_id: str) -> dict[str, Any]:
        """Return one published assessment package by identifier."""
        # Line comment: read one package record from the assessment item bank.
        return dict(self.stores.item_bank.get(assessment_id, {}))

    # Block comment:
    # This method handles submission command and downstream evidence publication.
    def submit_assessment(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Submit one assessment attempt and publish inference evidence."""
        # Line comment: build typed submission object from command payload.
        submission = AssessmentSubmission(
            attempt_id=str(payload["attempt_id"]),
            assessment_id=str(payload["assessment_id"]),
            employee_id=str(payload["employee_id"]),
            responses=dict(payload.get("responses", {})),
        )
        # Line comment: execute delivery/scoring flow and persist final score.
        final_score = self._impl.submit_assessment(submission)
        # Line comment: publish evidence into core inference and event bus.
        states = self._impl.publish_evidence(self.core_api, submission)
        # Line comment: return command response including emitted skill states.
        return {"attempt_id": submission.attempt_id, "score": final_score, "states": [asdict(state) for state in states]}

