"""Workflow orchestration primitives for long-running store update jobs."""

from __future__ import annotations

import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass
from typing import Any, Callable, Dict
from uuid import uuid4

try:
    from .stores import PlatformStores
except ImportError:
    from stores import PlatformStores


WorkflowHandler = Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]


@dataclass(frozen=True)
class WorkflowDefinition:
    """Registered workflow metadata and execution handler."""

    name: str
    container: str
    description: str
    store_targets: tuple[str, ...]
    handler: WorkflowHandler


class WorkflowOrchestrationService:
    """Queues, runs, and tracks long-running jobs that update platform stores."""

    # Block comment:
    # This initializer stores shared dependencies and defers worker creation until needed.
    def __init__(self, stores: PlatformStores, max_workers: int = 1) -> None:
        """Initialize workflow orchestration state for one platform instance."""
        # Line comment: keep shared stores so job state can be observed through the platform.
        self._stores = stores
        # Line comment: serialize registry and job record mutations across API callers and workers.
        self._lock = threading.RLock()
        # Line comment: defer worker-pool creation so platforms that never queue jobs stay lightweight.
        self._executor: ThreadPoolExecutor | None = None
        # Line comment: preserve configured concurrency for lazy executor initialization.
        self._max_workers = max(1, int(max_workers))
        # Line comment: keep registered workflow definitions by stable workflow name.
        self._definitions: dict[str, WorkflowDefinition] = {}
        # Line comment: keep job futures so callers can wait on background runs when needed.
        self._futures: dict[str, Future[dict[str, Any]]] = {}
        # Line comment: initialize shared workflow metadata stores used by admin/query surfaces.
        self._stores.meta.setdefault("workflow_jobs", {})
        self._stores.meta.setdefault("workflow_job_order", [])

    # Block comment:
    # This helper creates the executor lazily the first time a background job is submitted.
    def _get_executor(self) -> ThreadPoolExecutor:
        """Return the worker pool used for queued workflow jobs."""
        # Line comment: create the executor only once under the orchestration lock.
        with self._lock:
            if self._executor is None:
                self._executor = ThreadPoolExecutor(
                    max_workers=self._max_workers,
                    thread_name_prefix="skillsai-workflow",
                )
            return self._executor

    # Block comment:
    # This helper returns the shared in-memory job registry persisted in META.
    def _job_registry(self) -> dict[str, dict[str, Any]]:
        """Return the workflow job registry stored in platform metadata."""
        # Line comment: cast the metadata entry to the expected registry shape.
        return self._stores.meta.setdefault("workflow_jobs", {})

    # Block comment:
    # This helper returns the job ordering list used for newest-first query responses.
    def _job_order(self) -> list[str]:
        """Return the workflow job identifier order stored in platform metadata."""
        # Line comment: create the order list when the platform has not queued jobs yet.
        return self._stores.meta.setdefault("workflow_job_order", [])

    # Block comment:
    # This helper updates a stored job record atomically under the orchestration lock.
    def _update_job(self, job_id: str, **changes: Any) -> dict[str, Any]:
        """Apply field updates to one workflow job record and return a copy."""
        # Line comment: mutate the canonical in-memory record while holding the orchestration lock.
        with self._lock:
            job = self._job_registry()[job_id]
            job.update(changes)
            return dict(job)

    # Block comment:
    # This helper copies a stored job record so callers do not mutate shared state directly.
    def _copy_job(self, job_id: str) -> dict[str, Any]:
        """Return a detached copy of one workflow job record."""
        # Line comment: guard registry reads so callers see a stable snapshot.
        with self._lock:
            job = self._job_registry().get(job_id, {})
            return dict(job)

    # Block comment:
    # This method registers one named workflow so containers can submit jobs by name later.
    def register_workflow(
        self,
        name: str,
        handler: WorkflowHandler,
        *,
        container: str,
        description: str,
        store_targets: tuple[str, ...] = (),
    ) -> None:
        """Register one executable workflow definition."""
        # Line comment: persist workflow metadata and handler under the stable workflow name.
        with self._lock:
            self._definitions[name] = WorkflowDefinition(
                name=name,
                container=container,
                description=description,
                store_targets=store_targets,
                handler=handler,
            )

    # Block comment:
    # This method checks whether a named workflow definition already exists.
    def has_workflow(self, name: str) -> bool:
        """Return whether the requested workflow is registered."""
        # Line comment: perform the lookup under lock for consistency with registration.
        with self._lock:
            return name in self._definitions

    # Block comment:
    # This method creates a queued job record and submits its execution to the worker pool.
    def submit_workflow(
        self,
        name: str,
        payload: dict[str, Any] | None = None,
        *,
        trigger: str = "manual",
    ) -> dict[str, Any]:
        """Queue one registered workflow job and return its queued record."""
        # Line comment: validate the workflow name before creating a queued record.
        with self._lock:
            if name not in self._definitions:
                raise KeyError(f"Unknown workflow '{name}'.")
            definition = self._definitions[name]
            submitted_at = time.time()
            job_id = f"job-{uuid4().hex[:12]}"
            job_record = {
                "job_id": job_id,
                "workflow": name,
                "container": definition.container,
                "description": definition.description,
                "store_targets": list(definition.store_targets),
                "trigger": trigger,
                "state": "queued",
                "submitted_at": submitted_at,
                "started_at": None,
                "finished_at": None,
                "payload": dict(payload or {}),
                "result": None,
                "error": None,
            }
            # Line comment: persist the queued record before background execution starts.
            self._job_registry()[job_id] = job_record
            self._job_order().append(job_id)
        # Line comment: submit the execution wrapper to the serialized worker pool.
        future = self._get_executor().submit(
            self._run_workflow_job,
            definition,
            job_id,
            dict(payload or {}),
            trigger,
        )
        with self._lock:
            self._futures[job_id] = future
        return dict(job_record)

    # Block comment:
    # This worker wrapper transitions one queued job through running and terminal states.
    def _run_workflow_job(
        self,
        definition: WorkflowDefinition,
        job_id: str,
        payload: dict[str, Any],
        trigger: str,
    ) -> dict[str, Any]:
        """Execute one workflow definition and persist terminal job state."""
        # Line comment: mark the job as running with a precise start timestamp.
        started_at = time.time()
        self._update_job(job_id, state="running", started_at=started_at)
        job_context = {
            "job_id": job_id,
            "workflow": definition.name,
            "container": definition.container,
            "store_targets": list(definition.store_targets),
            "trigger": trigger,
            "started_at": started_at,
        }
        try:
            # Line comment: execute the registered workflow handler with payload and job metadata.
            result = definition.handler(dict(payload), dict(job_context))
        except Exception as exc:
            # Line comment: persist a failure state and re-raise so waiting callers observe the error.
            self._update_job(
                job_id,
                state="failed",
                finished_at=time.time(),
                error=str(exc),
            )
            raise
        # Line comment: persist a completed terminal state alongside the workflow result payload.
        self._update_job(
            job_id,
            state="completed",
            finished_at=time.time(),
            result=result,
        )
        return result

    # Block comment:
    # This method returns one stored job record by identifier for query and admin surfaces.
    def get_job(self, job_id: str) -> dict[str, Any]:
        """Return one workflow job record by identifier."""
        # Line comment: raise when the requested job id is unknown to the registry.
        job = self._copy_job(job_id)
        if not job:
            raise KeyError(f"Unknown workflow job '{job_id}'.")
        return job

    # Block comment:
    # This method returns recent jobs in newest-first order for user-facing status views.
    def list_jobs(self, limit: int | None = None) -> list[dict[str, Any]]:
        """Return workflow jobs ordered from newest to oldest."""
        # Line comment: normalize the optional limit before copying job records.
        normalized_limit = None if limit is None else max(0, int(limit))
        with self._lock:
            ordered_job_ids = list(reversed(self._job_order()))
            if normalized_limit is not None:
                ordered_job_ids = ordered_job_ids[:normalized_limit]
            return [dict(self._job_registry()[job_id]) for job_id in ordered_job_ids]

    # Block comment:
    # This method waits for one background job and then returns the latest stored job record.
    def wait_for_job(self, job_id: str, timeout_seconds: float | None = None) -> dict[str, Any]:
        """Wait for one workflow job to finish and return its final record."""
        # Line comment: look up the submitted future so callers can block on completion.
        with self._lock:
            future = self._futures.get(job_id)
        if future is None:
            return self.get_job(job_id)
        try:
            # Line comment: wait on the underlying worker future using the requested timeout.
            future.result(timeout=timeout_seconds)
        except TimeoutError as exc:
            raise TimeoutError(f"Workflow job '{job_id}' did not finish before timeout.") from exc
        return self.get_job(job_id)

    # Block comment:
    # This helper summarizes high-level workflow status for admin and debugging views.
    def summarize_jobs(self) -> dict[str, Any]:
        """Return aggregate workflow job counts and the latest queued/completed job."""
        # Line comment: gather all job records once so summary counters stay internally consistent.
        jobs = self.list_jobs()
        state_counts: dict[str, int] = {}
        for job in jobs:
            # Line comment: increment a simple count per terminal or in-flight state.
            state = str(job.get("state", "unknown"))
            state_counts[state] = state_counts.get(state, 0) + 1
        # Line comment: return compact aggregate metadata plus the newest job record when available.
        return {
            "total_jobs": len(jobs),
            "state_counts": state_counts,
            "latest_job": jobs[0] if jobs else None,
        }
