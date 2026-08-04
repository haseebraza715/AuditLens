from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any, Callable, Literal
from uuid import uuid4

JobStatus = Literal["queued", "running", "complete", "failed"]

_TERMINAL_STATUSES = {"complete", "failed"}


class ReportJobStore:
    """Process-local job registry (see tests/reporting/test_job_store_contract.py).

    Terminal jobs are evicted by age and count so a long-lived server stays
    bounded; queued and running jobs are never evicted.
    """

    def __init__(
        self,
        *,
        terminal_ttl_seconds: float = 24 * 3600,
        max_terminal_jobs: int = 500,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if terminal_ttl_seconds <= 0 or max_terminal_jobs < 1:
            raise ValueError("terminal_ttl_seconds and max_terminal_jobs must be positive")
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._terminal_ttl_seconds = terminal_ttl_seconds
        self._max_terminal_jobs = max_terminal_jobs
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def create_job(self) -> dict[str, Any]:
        job_id = str(uuid4())
        now = self._clock().isoformat()
        job = {
            "job_id": job_id,
            "status": "queued",
            "created_at_utc": now,
            "updated_at_utc": now,
            "result": None,
            "error": None,
        }
        with self._lock:
            self._evict_terminal_jobs()
            self._jobs[job_id] = job
        return dict(job)

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None

    def update_job(self, job_id: str, **fields: Any) -> dict[str, Any] | None:
        with self._lock:
            if job_id not in self._jobs:
                return None
            self._jobs[job_id].update(fields)
            self._jobs[job_id]["updated_at_utc"] = self._clock().isoformat()
            self._evict_terminal_jobs()
            return dict(self._jobs[job_id])

    def _evict_terminal_jobs(self) -> None:
        """Drop terminal jobs past their TTL, then the oldest beyond the cap."""
        now = self._clock()
        kept: list[tuple[datetime, str]] = []
        for job_id, job in list(self._jobs.items()):
            if job["status"] not in _TERMINAL_STATUSES:
                continue
            updated_at = datetime.fromisoformat(str(job["updated_at_utc"]))
            if (now - updated_at).total_seconds() > self._terminal_ttl_seconds:
                del self._jobs[job_id]
            else:
                kept.append((updated_at, job_id))
        kept.sort(key=lambda entry: entry[0])
        overflow = len(kept) - self._max_terminal_jobs
        for _, job_id in kept[: max(overflow, 0)]:
            del self._jobs[job_id]


report_job_store = ReportJobStore()


def start_report_job(job_id: str, worker: Callable[[], dict[str, Any]]) -> None:
    def _run() -> None:
        report_job_store.update_job(job_id, status="running")
        try:
            result = worker()
            report_job_store.update_job(job_id, status="complete", result=result, error=None)
        except Exception as exc:  # pragma: no cover
            report_job_store.update_job(job_id, status="failed", error=str(exc), result=None)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
