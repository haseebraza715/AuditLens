from __future__ import annotations

import io

import pytest

pytest.importorskip("fastapi")
from auditlens_server.app import app
from auditlens_server.routers import audit as audit_router
from fastapi.testclient import TestClient

client = TestClient(app)


class _CountingFile(io.BytesIO):
    """Records the largest single read request made by the handler."""

    def __init__(self, payload: bytes) -> None:
        super().__init__(payload)
        self.max_requested: int | None = None

    def read(self, size: int = -1) -> bytes:  # type: ignore[override]
        if self.max_requested is None or size > self.max_requested:
            self.max_requested = size
        return super().read(size)


def test_bounded_reader_never_requests_more_than_limit_plus_one(monkeypatch) -> None:
    monkeypatch.setenv("AUDITLENS_MAX_UPLOAD_BYTES", "16")

    class _Upload:
        file = _CountingFile(b"a,b\n" * 100)

    raw = audit_router._read_upload_bounded(_Upload())

    assert _Upload.file.max_requested == 17
    assert len(raw) == 17


def test_expired_artifact_returns_410_and_is_removed(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AUDITLENS_ARTIFACT_DIR", str(tmp_path))
    from auditlens.reporting.artifacts import save_report_artifact

    metadata = save_report_artifact(
        artifact_format="markdown",
        filename="report.md",
        content="# report",
        retention_hours=1,
    )
    artifact_id = str(metadata["artifact_id"])
    monkeypatch.setattr(audit_router, "artifact_is_expired", lambda _metadata: True)

    response = client.get(f"/reports/{artifact_id}")

    assert response.status_code == 410
    assert not (tmp_path / f"{artifact_id}.json").exists()

    follow_up = client.get(f"/reports/{artifact_id}/download")
    assert follow_up.status_code == 404
