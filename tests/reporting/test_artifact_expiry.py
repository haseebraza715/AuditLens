from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from auditlens.reporting.artifacts import (
    artifact_is_expired,
    delete_artifact,
    get_artifact_metadata,
    purge_expired_artifacts,
    save_report_artifact,
)


def _save(tmp_path: Path) -> dict[str, object]:
    return save_report_artifact(
        artifact_format="markdown",
        filename="report.md",
        content="# report",
        retention_hours=1,
        artifact_dir=tmp_path,
    )


def test_artifact_not_expired_before_deadline(tmp_path: Path) -> None:
    metadata = _save(tmp_path)
    created = datetime.fromisoformat(str(metadata["created_at_utc"]))
    assert not artifact_is_expired(metadata, now=created + timedelta(minutes=59))


def test_artifact_expired_after_deadline(tmp_path: Path) -> None:
    metadata = _save(tmp_path)
    created = datetime.fromisoformat(str(metadata["created_at_utc"]))
    assert artifact_is_expired(metadata, now=created + timedelta(hours=1, seconds=1))


def test_purge_removes_only_expired_artifacts(tmp_path: Path) -> None:
    expired = _save(tmp_path)
    fresh = save_report_artifact(
        artifact_format="markdown",
        filename="fresh.md",
        content="# fresh",
        retention_hours=48,
        artifact_dir=tmp_path,
    )
    later = datetime.now(timezone.utc) + timedelta(hours=2)

    purged = purge_expired_artifacts(artifact_dir=tmp_path, now=later)

    assert purged == 1
    assert not Path(str(expired["storage_path"])).exists()
    assert Path(str(fresh["storage_path"])).exists()
    assert get_artifact_metadata(str(fresh["artifact_id"]), artifact_dir=tmp_path)


def test_delete_artifact_removes_metadata_and_content(tmp_path: Path) -> None:
    metadata = _save(tmp_path)
    artifact_id = str(metadata["artifact_id"])

    delete_artifact(artifact_id, artifact_dir=tmp_path)

    assert not Path(str(metadata["storage_path"])).exists()
    assert not (tmp_path / f"{artifact_id}.json").exists()
