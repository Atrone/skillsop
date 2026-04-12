"""Analytics & longitudinal container components (Level 3D)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

try:
    from ..event_bus import PlatformEventBus
    from ..models import KPIQuery
    from ..stores import PlatformStores
    from ..workflow_orchestration import WorkflowOrchestrationService
except ImportError:
    from event_bus import PlatformEventBus
    from models import KPIQuery
    from stores import PlatformStores
    from workflow_orchestration import WorkflowOrchestrationService


MATERIALIZATION_WORKFLOW_NAME = "analytics.materialization"


@dataclass
class AnalyticsService:
    """Implements Analytics API and query stack components."""

    stores: PlatformStores

    # Block comment:
    # This endpoint mirrors the Analytics API plus Semantic Query Layer.
    def run_query(self, query: KPIQuery) -> dict[str, Any]:
        """Execute KPI/trend/planning query and render dashboard payload."""
        # Line comment: build a semantic query plan from caller parameters.
        plan = self._semantic_query_layer(query)
        # Line comment: execute the plan against the needed data views.
        data = self._execute_plan(plan)
        # Line comment: return a dashboard-friendly envelope.
        return self._dashboard_renderer(query, data)

    # Block comment:
    # Semantic query layer decides which engines and stores are needed.
    def _semantic_query_layer(self, query: KPIQuery) -> dict[str, Any]:
        """Parse metric intent and create an execution plan."""
        # Line comment: simple rule-based plan selection for demo architecture.
        if query.metric.startswith("trend."):
            engine = "trend"
        elif query.metric.startswith("plan."):
            engine = "planning"
        else:
            engine = "kpi"
        # Line comment: include shared filters used by all engines.
        return {
            "engine": engine,
            "metric": query.metric,
            "cohort": query.cohort,
            "start": query.start,
            "end": query.end,
        }

    # Block comment:
    # This method dispatches to KPI, trend/cohort, or planning models.
    def _execute_plan(self, plan: dict[str, Any]) -> dict[str, Any]:
        """Execute one semantic plan using the mapped analytics engine."""
        # Line comment: evaluate the designated engine.
        engine = plan["engine"]
        if engine == "trend":
            # Line comment: trend and cohort analyzer path.
            return self._trend_and_cohort_analyzer(plan)
        if engine == "planning":
            # Line comment: workforce planning modeler path.
            return self._workforce_planning_modeler(plan)
        # Line comment: default KPI query engine path.
        return self._kpi_query_engine(plan)

    # Block comment:
    # KPI query engine reads current-state derived metrics and graph views.
    def _kpi_query_engine(self, plan: dict[str, Any]) -> dict[str, Any]:
        """Execute current KPI query against MART and graph aggregates."""
        # Line comment: retrieve metric value from mart with a deterministic key.
        mart_key = f"{plan['metric']}:{plan['cohort']}"
        value = self.stores.mart.get(mart_key, 0.0)
        # Line comment: expose graph size as extra context.
        graph_nodes = len(self.stores.graph)
        return {"value": value, "graph_nodes": graph_nodes}

    # Block comment:
    # Trend analyzer reads the warehouse and time-series stores.
    def _trend_and_cohort_analyzer(self, plan: dict[str, Any]) -> dict[str, Any]:
        """Execute trend query from historical warehouse snapshots."""
        # Line comment: collect historical points matching the target metric.
        points = [
            row["value"]
            for row in self.stores.warehouse
            if row.get("metric") == plan["metric"] and row.get("cohort") == plan["cohort"]
        ]
        # Line comment: compute simple summary statistics for trend view.
        if not points:
            return {"series": [], "average": 0.0}
        return {"series": points, "average": sum(points) / len(points)}

    # Block comment:
    # Planning modeler approximates scenario projection from historical baseline.
    def _workforce_planning_modeler(self, plan: dict[str, Any]) -> dict[str, Any]:
        """Compute lightweight workforce scenario outputs."""
        # Line comment: use existing mart metric as baseline signal.
        baseline = float(self.stores.mart.get(f"baseline:{plan['cohort']}", 1.0))
        # Line comment: return deterministic scenario alternatives.
        return {"conservative": baseline * 0.95, "target": baseline, "aggressive": baseline * 1.1}

    # Block comment:
    # Dashboard renderer standardizes payload shape for managers/analysts.
    def _dashboard_renderer(self, query: KPIQuery, data: dict[str, Any]) -> dict[str, Any]:
        """Render a dashboard payload from query and data results."""
        # Line comment: create a consistent analytics response envelope.
        return {
            "metric": query.metric,
            "cohort": query.cohort,
            "range": {"start": query.start, "end": query.end},
            "data": data,
        }


@dataclass
class SnapshotScheduler:
    """Implements schedule, dependency, orchestration, and run ledger."""

    stores: PlatformStores
    run_counter: int = 0

    # Block comment:
    # Scheduler receives refresh trigger and executes one materialization run.
    def trigger_refresh(self) -> dict[str, Any]:
        """Run dependency resolution and orchestration for one refresh cycle."""
        # Line comment: plan dependency graph for the requested snapshot run.
        dependency_graph = self._dependency_resolver()
        # Line comment: execute the plan and produce run outcomes.
        outcome = self._execution_orchestrator(dependency_graph)
        return outcome

    # Block comment:
    # Dependency resolver mirrors explicit sequencing in the architecture diagram.
    def _dependency_resolver(self) -> list[str]:
        """Build ordered dependency list for KPI materialization tasks."""
        # Line comment: produce a stable task order for orchestrator.
        return ["load_kpi_definitions", "calculate_metrics", "aggregate", "snapshot", "publish"]

    # Block comment:
    # Orchestrator executes dependencies and writes to run ledger.
    def _execution_orchestrator(self, tasks: list[str]) -> dict[str, Any]:
        """Execute ordered tasks and persist run-state in ledger."""
        # Line comment: advance run id for each scheduler execution.
        self.run_counter += 1
        run_id = f"run-{self.run_counter}"
        # Line comment: call backfill manager before ledger write.
        backfill_info = self._backfill_manager(tasks)
        # Line comment: append run state to ledger list in meta store.
        ledger = self.stores.meta.setdefault("run_ledger", [])
        entry = {"run_id": run_id, "tasks": tasks, "backfill": backfill_info, "state": "success"}
        ledger.append(entry)
        return entry

    # Block comment:
    # Backfill manager records recompute policy metadata for each run.
    def _backfill_manager(self, tasks: list[str]) -> dict[str, Any]:
        """Create backfill metadata associated with orchestration run."""
        # Line comment: provide deterministic sample metadata for backfill policy.
        return {"recomputed_tasks": list(tasks), "mode": "incremental"}


@dataclass
class KPIMaterializer:
    """Implements KPI definition load, calc, aggregation, and publish."""

    stores: PlatformStores
    definitions: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Block comment:
    # Materialization pipeline executes full KPI definition to warehouse publish.
    def materialize(self) -> list[dict[str, Any]]:
        """Run KPI materialization pipeline and return published rows."""
        # Line comment: load effective-dated KPI definitions from metadata store.
        loaded = self._kpi_definition_loader()
        # Line comment: calculate raw metric values from event and mart inputs.
        calculated = self._metric_calculation_engine(loaded)
        # Line comment: aggregate raw values into cohort dimensions.
        aggregated = self._aggregation_engine(calculated)
        # Line comment: build snapshots and publish dimensional rows.
        snapshots = self._snapshot_builder(aggregated)
        return self._dimensional_publisher(snapshots)

    # Block comment:
    # Definition loader retrieves versioned KPI definitions from META.
    def _kpi_definition_loader(self) -> dict[str, dict[str, Any]]:
        """Load KPI definitions and cache them locally for one run."""
        # Line comment: copy definitions so run operations do not mutate source.
        raw_defs = self.stores.meta.get("kpi_definitions", {})
        self.definitions = dict(raw_defs)
        return self.definitions

    # Block comment:
    # Calculation engine computes metrics from TS history and MART snapshots.
    def _metric_calculation_engine(self, definitions: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        """Compute raw metric values from KPI definitions."""
        # Line comment: count event records as a lightweight historical measure.
        event_count = len(self.stores.time_series)
        # Line comment: convert each definition into a raw metric data point.
        outputs: list[dict[str, Any]] = []
        for metric, definition in definitions.items():
            multiplier = float(definition.get("multiplier", 1.0))
            cohort = definition.get("cohort", "all")
            value = event_count * multiplier
            outputs.append({"metric": metric, "cohort": cohort, "value": value})
        return outputs

    # Block comment:
    # Aggregation engine merges raw rows into combined metric/cohort totals.
    def _aggregation_engine(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Aggregate raw metric rows into cohort-level totals."""
        # Line comment: accumulate row values keyed by metric and cohort.
        aggregates: dict[str, float] = {}
        for row in rows:
            key = f"{row['metric']}:{row['cohort']}"
            aggregates[key] = aggregates.get(key, 0.0) + float(row["value"])
        # Line comment: materialize aggregate dictionary back into row objects.
        return [
            {"metric": key.split(":")[0], "cohort": key.split(":")[1], "value": value}
            for key, value in aggregates.items()
        ]

    # Block comment:
    # Snapshot builder creates effective-dated time slices for aggregate rows.
    def _snapshot_builder(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Create dated snapshot rows for warehouse publishing."""
        # Line comment: stamp all rows with one deterministic snapshot date.
        return [{**row, "snapshot_date": "2026-04-09"} for row in rows]

    # Block comment:
    # Dimensional publisher writes snapshots into analytics warehouse store.
    def _dimensional_publisher(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Publish dimensional rows to analytics warehouse."""
        # Line comment: append each row and mirror key metric in mart for API reads.
        for row in rows:
            self.stores.append("warehouse", row)
            mart_key = f"{row['metric']}:{row['cohort']}"
            self.stores.mart[mart_key] = row["value"]
        return rows


@dataclass
class AnalyticsLongitudinalContainer:
    """Container façade for analytics API, scheduler, and KPI materializer."""

    stores: PlatformStores
    event_bus: PlatformEventBus
    workflow_service: WorkflowOrchestrationService | None = None
    analytics_service: AnalyticsService = field(init=False)
    scheduler: SnapshotScheduler = field(init=False)
    materializer: KPIMaterializer = field(init=False)

    # Block comment:
    # This initializer wires analytics components to the shared workflow orchestration service.
    def __post_init__(self) -> None:
        """Initialize all Level 3D component façades."""
        # Line comment: instantiate internal analytics service components.
        self.analytics_service = AnalyticsService(self.stores)
        self.scheduler = SnapshotScheduler(self.stores)
        self.materializer = KPIMaterializer(self.stores)
        # Line comment: create a local workflow service only when platform composition did not supply one.
        if self.workflow_service is None:
            self.workflow_service = WorkflowOrchestrationService(self.stores)
        # Line comment: register the analytics materialization workflow once per shared service instance.
        if not self.workflow_service.has_workflow(MATERIALIZATION_WORKFLOW_NAME):
            self.workflow_service.register_workflow(
                MATERIALIZATION_WORKFLOW_NAME,
                self._execute_materialization_workflow,
                container="analytics_longitudinal",
                description="Refresh KPI snapshots and publish warehouse updates.",
                store_targets=("meta", "warehouse", "mart"),
            )

    # Block comment:
    # This workflow handler performs the full scheduler-plus-materializer store update run.
    def _execute_materialization_workflow(
        self,
        payload: dict[str, Any],
        job_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute one analytics materialization workflow job."""
        # Line comment: run the scheduler first so the run ledger is updated before publication.
        run = self.scheduler.trigger_refresh()
        # Line comment: materialize KPI rows into warehouse and mart stores for downstream reads.
        published = self.materializer.materialize()
        return {
            "job_id": str(job_context["job_id"]),
            "trigger": str(payload.get("trigger", job_context.get("trigger", "manual"))),
            "run": run,
            "published_rows": len(published),
            "published_metrics": [str(row.get("metric", "")) for row in published],
        }

    # Block comment:
    # This method handles event-bus refresh triggers and schedules a run.
    def handle_bus_event(self, payload: dict[str, Any]) -> None:
        """Consume a bus event and run one refresh/materialization cycle."""
        # Line comment: derive a readable trigger label from the incoming bus payload when present.
        trigger = str(payload.get("reason", payload.get("event", "event_bus")))
        workflow_response = self.trigger_materialization(trigger=trigger, wait_for_completion=False)
        # Line comment: expose the latest background refresh job for admin/debug surfaces.
        self.stores.meta["latest_workflow_job_id"] = workflow_response["job"]["job_id"]

    # Block comment:
    # This method executes read analytics queries from the federation gateway.
    def analytics_query(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute analytics API query against semantic query layer."""
        # Line comment: construct typed query object from gateway payload.
        query = KPIQuery(
            metric=str(payload.get("metric", "skill_coverage")),
            cohort=str(payload.get("cohort", "all")),
            start=str(payload.get("start", "2026-01-01")),
            end=str(payload.get("end", "2026-12-31")),
        )
        return self.analytics_service.run_query(query)

    # Block comment:
    # This method exposes explicit materialization command handling through the workflow service.
    def trigger_materialization(self, trigger: str = "manual", wait_for_completion: bool = True) -> dict[str, Any]:
        """Queue or run an analytics materialization workflow job."""
        # Line comment: submit the workflow job using the stable analytics materialization definition.
        job = self.workflow_service.submit_workflow(
            MATERIALIZATION_WORKFLOW_NAME,
            {"trigger": trigger},
            trigger=trigger,
        )
        if not wait_for_completion:
            # Line comment: return the queued job immediately for long-running background execution.
            return {"trigger": trigger, "mode": "background", "job": job}
        # Line comment: block until the background worker finishes so synchronous callers stay deterministic.
        completed_job = self.workflow_service.wait_for_job(job["job_id"])
        result = dict(completed_job.get("result") or {})
        return {
            "trigger": trigger,
            "mode": "synchronous",
            "job": completed_job,
            "run": result.get("run", {}),
            "published_rows": int(result.get("published_rows", 0)),
        }

    # Block comment:
    # This method exposes workflow job listings for admin views and debugging endpoints.
    def list_workflow_jobs(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return recent analytics workflow jobs from newest to oldest."""
        # Line comment: delegate listing to the shared workflow orchestration service.
        return self.workflow_service.list_jobs(limit=limit)

    # Block comment:
    # This method exposes one workflow job record for status polling and debugging.
    def get_workflow_job(self, job_id: str) -> dict[str, Any]:
        """Return one analytics workflow job by identifier."""
        # Line comment: delegate lookup to the shared workflow orchestration service.
        return self.workflow_service.get_job(job_id)

    # Block comment:
    # This helper allows tests and API callers to block on one background workflow job.
    def wait_for_workflow_job(self, job_id: str, timeout_seconds: float | None = None) -> dict[str, Any]:
        """Wait for one analytics workflow job to finish."""
        # Line comment: return the final workflow job record after the worker completes.
        return self.workflow_service.wait_for_job(job_id, timeout_seconds=timeout_seconds)
