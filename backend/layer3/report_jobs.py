from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any, Callable, Literal
from uuid import uuid4


JobStatus = Literal["queued", "running", "complete", "failed"]


class ReportJobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create_job(self) -> dict[str, Any]:
        job_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        job = {
            "job_id": job_id,
            "status": "queued",
            "created_at_utc": now,
            "updated_at_utc": now,
            "result": None,
            "error": None,
        }
        with self._lock:
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
            self._jobs[job_id]["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
            return dict(self._jobs[job_id])


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

