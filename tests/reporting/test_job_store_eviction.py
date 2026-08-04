from __future__ import annotations

from datetime import datetime, timedelta, timezone

from auditlens.reporting.jobs import ReportJobStore


class FakeClock:
    def __init__(self) -> None:
        self.now = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kwargs: float) -> None:
        self.now += timedelta(**kwargs)


def test_terminal_jobs_evicted_after_ttl() -> None:
    clock = FakeClock()
    store = ReportJobStore(terminal_ttl_seconds=3600, clock=clock)
    job_id = str(store.create_job()["job_id"])
    store.update_job(job_id, status="complete", result={"ok": True})

    clock.advance(hours=2)
    store.create_job()  # any write triggers eviction

    assert store.get_job(job_id) is None


def test_running_and_queued_jobs_never_evicted() -> None:
    clock = FakeClock()
    store = ReportJobStore(terminal_ttl_seconds=1, max_terminal_jobs=1, clock=clock)
    queued_id = str(store.create_job()["job_id"])
    running_id = str(store.create_job()["job_id"])
    store.update_job(running_id, status="running")

    clock.advance(days=30)
    store.create_job()

    assert store.get_job(queued_id) is not None
    assert store.get_job(running_id) is not None


def test_terminal_jobs_capped_by_count_oldest_first() -> None:
    clock = FakeClock()
    store = ReportJobStore(max_terminal_jobs=2, clock=clock)
    ids = []
    for _ in range(3):
        job_id = str(store.create_job()["job_id"])
        store.update_job(job_id, status="complete", result=None)
        ids.append(job_id)
        clock.advance(seconds=10)

    store.create_job()

    assert store.get_job(ids[0]) is None
    assert store.get_job(ids[1]) is not None
    assert store.get_job(ids[2]) is not None
