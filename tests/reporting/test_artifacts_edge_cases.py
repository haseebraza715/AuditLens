"""Validation and boundary tests for report artifact persistence."""

from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta

import pytest

from auditlens.reporting.artifacts import (
    ArtifactNotFoundError,
    artifact_is_expired,
    delete_artifact,
    get_artifact_metadata,
    purge_expired_artifacts,
    save_report_artifact,
)


class TestSaveValidation:
    def test_unknown_format_raises_value_error(self, tmp_path) -> None:
        with pytest.raises(ValueError, match="Unsupported artifact format"):
            save_report_artifact(
                artifact_format="html", filename="x.html", content="<html>", artifact_dir=tmp_path
            )

    def test_invalid_base64_raises_clear_value_error(self, tmp_path) -> None:
        with pytest.raises(ValueError, match="valid base64"):
            save_report_artifact(
                artifact_format="pdf_base64", filename="x.pdf", content="not-base64!!!", artifact_dir=tmp_path
            )

    def test_empty_string_base64_is_accepted(self, tmp_path) -> None:
        meta = save_report_artifact(
            artifact_format="pdf_base64", filename="x.pdf", content="", artifact_dir=tmp_path
        )
        assert meta["media_type"] == "application/pdf"

    def test_invalid_base64_leaves_no_partial_files(self, tmp_path) -> None:
        with pytest.raises(ValueError):
            save_report_artifact(
                artifact_format="pdf_base64", filename="x.pdf", content="!!!", artifact_dir=tmp_path
            )
        assert list(tmp_path.iterdir()) == []

    def test_retention_hours_are_clamped_to_one(self, tmp_path) -> None:
        meta = save_report_artifact(
            artifact_format="markdown",
            filename="r.md",
            content="# r",
            retention_hours=0,
            artifact_dir=tmp_path,
        )
        created = datetime.fromisoformat(meta["created_at_utc"])
        expires = datetime.fromisoformat(meta["expires_at_utc"])
        assert expires - created == timedelta(hours=1)

    def test_filename_and_content_preserved(self, tmp_path) -> None:
        content = "# AuditLens\n\nRésumé — αβγ\n"
        meta = save_report_artifact(
            artifact_format="markdown", filename="résumé.md", content=content, artifact_dir=tmp_path
        )
        loaded = get_artifact_metadata(meta["artifact_id"], artifact_dir=tmp_path)
        assert loaded["filename"] == "résumé.md"
        stored = (tmp_path / f"{meta['artifact_id']}.md").read_text(encoding="utf-8")
        assert stored == content

    def test_artifact_dir_is_created_on_demand(self, tmp_path) -> None:
        nested = tmp_path / "a" / "b"
        meta = save_report_artifact(
            artifact_format="markdown", filename="r.md", content="x", artifact_dir=nested
        )
        assert (nested / f"{meta['artifact_id']}.md").exists()


class TestArtifactAccess:
    def test_missing_artifact_raises_not_found(self, tmp_path) -> None:
        with pytest.raises(ArtifactNotFoundError):
            get_artifact_metadata("00000000-0000-0000-0000-000000000000", artifact_dir=tmp_path)

    def test_non_uuid_id_raises_not_found_not_traversal(self, tmp_path) -> None:
        with pytest.raises(ArtifactNotFoundError):
            get_artifact_metadata("../../etc/passwd", artifact_dir=tmp_path)

    def test_delete_missing_artifact_is_silent(self, tmp_path) -> None:
        delete_artifact("00000000-0000-0000-0000-000000000000", artifact_dir=tmp_path)

    def test_expired_metadata_is_reported(self, tmp_path) -> None:
        meta = save_report_artifact(
            artifact_format="markdown", filename="r.md", content="x", artifact_dir=tmp_path
        )
        now = datetime.fromisoformat(meta["expires_at_utc"]) + timedelta(seconds=1)
        assert artifact_is_expired(meta, now=now)
        assert not artifact_is_expired(meta, now=now - timedelta(hours=1))

    def test_malformed_expiry_metadata_not_expired(self) -> None:
        assert not artifact_is_expired({"expires_at_utc": "not-a-date"})
        assert not artifact_is_expired({})


class TestPurge:
    def test_purge_only_removes_expired(self, tmp_path) -> None:
        fresh = save_report_artifact(
            artifact_format="markdown", filename="fresh.md", content="x",
            retention_hours=168, artifact_dir=tmp_path,
        )
        old = save_report_artifact(
            artifact_format="markdown", filename="old.md", content="y",
            retention_hours=1, artifact_dir=tmp_path,
        )
        expired = datetime.fromisoformat(old["expires_at_utc"])
        purged = purge_expired_artifacts(artifact_dir=tmp_path, now=expired + timedelta(seconds=1))
        assert purged == 1
        get_artifact_metadata(fresh["artifact_id"], artifact_dir=tmp_path)
        with pytest.raises(ArtifactNotFoundError):
            get_artifact_metadata(old["artifact_id"], artifact_dir=tmp_path)

    def test_purge_ignores_corrupt_metadata(self, tmp_path) -> None:
        meta = save_report_artifact(
            artifact_format="markdown", filename="r.md", content="x", artifact_dir=tmp_path
        )
        (tmp_path / f"{meta['artifact_id']}.json").write_text("not json", encoding="utf-8")
        assert purge_expired_artifacts(artifact_dir=tmp_path) == 0

    def test_purge_empty_dir_returns_zero(self, tmp_path) -> None:
        assert purge_expired_artifacts(artifact_dir=tmp_path) == 0


class TestMetadataContent:
    def test_metadata_json_is_well_formed(self, tmp_path) -> None:
        meta = save_report_artifact(
            artifact_format="markdown", filename="r.md", content="x", artifact_dir=tmp_path
        )
        raw = json.loads((tmp_path / f"{meta['artifact_id']}.json").read_text(encoding="utf-8"))
        assert raw["artifact_id"] == meta["artifact_id"]
        assert raw["format"] == "markdown"
        assert raw["storage_path"].endswith(".md")

    def test_pdf_artifact_roundtrips_exact_bytes(self, tmp_path) -> None:
        pdf_bytes = b"%PDF-1.4\n%%EOF\n" + bytes(range(256))
        encoded = base64.b64encode(pdf_bytes).decode("ascii")
        meta = save_report_artifact(
            artifact_format="pdf_base64", filename="x.pdf", content=encoded, artifact_dir=tmp_path
        )
        stored = (tmp_path / f"{meta['artifact_id']}.pdf").read_bytes()
        assert stored == pdf_bytes
