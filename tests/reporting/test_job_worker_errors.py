"""Async job worker failure and lifecycle tests."""

from __future__ import annotations

import time

from auditlens.reporting.jobs import ReportJobStore, start_report_job


def test_worker_success_marks_job_complete() -> None:
    store = ReportJobStore()
    job = store.create_job()
    start_report_job(job["job_id"], lambda: {"ok": True}, store=store)
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        status = store.get_job(job["job_id"])
        assert status is not None
        if status["status"] in {"complete", "failed"}:
            break
        time.sleep(0.01)
    assert status["status"] == "complete"
    assert status["result"] == {"ok": True}
    assert status["error"] is None


def test_worker_exception_marks_job_failed_with_message() -> None:
    store = ReportJobStore()
    job = store.create_job()

    def _boom() -> dict:
        raise ValueError("worker exploded")

    start_report_job(job["job_id"], _boom, store=store)
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        status = store.get_job(job["job_id"])
        assert status is not None
        if status["status"] in {"complete", "failed"}:
            break
        time.sleep(0.01)
    assert status["status"] == "failed"
    assert status["result"] is None
    assert status["error"] == "worker exploded"


def test_update_job_on_missing_job_returns_none() -> None:
    store = ReportJobStore()
    assert store.update_job("does-not-exist", status="running") is None


def test_create_job_starts_queued() -> None:
    store = ReportJobStore()
    job = store.create_job()
    assert job["status"] == "queued"
    assert job["created_at_utc"] == job["updated_at_utc"]
    assert job["result"] is None
    assert job["error"] is None
