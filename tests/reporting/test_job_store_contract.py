from concurrent.futures import ThreadPoolExecutor

from auditlens.reporting.jobs import ReportJobStore


def test_concurrent_job_creation_is_unique_and_visible() -> None:
    store = ReportJobStore()
    with ThreadPoolExecutor(max_workers=8) as executor:
        jobs = list(executor.map(lambda _: store.create_job(), range(64)))
    ids = {job["job_id"] for job in jobs}
    assert len(ids) == 64
    assert all(store.get_job(job_id) is not None for job_id in ids)


def test_job_store_is_explicitly_process_local_and_not_restart_persistent() -> None:
    first = ReportJobStore()
    job = first.create_job()
    restarted = ReportJobStore()
    assert restarted.get_job(job["job_id"]) is None
