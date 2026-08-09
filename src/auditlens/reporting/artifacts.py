from __future__ import annotations

import base64
import binascii
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4


class ArtifactNotFoundError(FileNotFoundError):
    pass


def _validate_artifact_id(artifact_id: str) -> None:
    """Artifact ids are UUIDs; anything else could traverse the artifact dir."""
    try:
        UUID(str(artifact_id))
    except (ValueError, AttributeError):
        raise ArtifactNotFoundError(f"Artifact '{artifact_id}' was not found")


def _resolve_root(artifact_dir: str | os.PathLike[str] | None) -> Path:
    if artifact_dir is not None:
        root = Path(artifact_dir)
    else:
        configured = os.getenv("AUDITLENS_ARTIFACT_DIR", ".auditlens_artifacts").strip() or ".auditlens_artifacts"
        root = Path(configured)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _metadata_path(artifact_id: str, *, artifact_dir: str | os.PathLike[str] | None) -> Path:
    return _resolve_root(artifact_dir) / f"{artifact_id}.json"


def _content_path(artifact_id: str, extension: str, *, artifact_dir: str | os.PathLike[str] | None) -> Path:
    return _resolve_root(artifact_dir) / f"{artifact_id}.{extension}"


def save_report_artifact(
    *,
    artifact_format: str,
    filename: str,
    content: str,
    retention_hours: int = 168,
    artifact_dir: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    artifact_id = str(uuid4())
    created_at = datetime.now(timezone.utc)
    expires_at = created_at + timedelta(hours=max(retention_hours, 1))

    if artifact_format == "markdown":
        extension = "md"
        media_type = "text/markdown; charset=utf-8"
        content_path = _content_path(artifact_id, extension, artifact_dir=artifact_dir)
        content_path.write_text(content, encoding="utf-8")
    elif artifact_format == "pdf_base64":
        try:
            content_bytes = base64.b64decode(content, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError(
                "pdf_base64 artifact content must be valid base64"
            ) from exc
        extension = "pdf"
        media_type = "application/pdf"
        content_path = _content_path(artifact_id, extension, artifact_dir=artifact_dir)
        content_path.write_bytes(content_bytes)
    else:
        raise ValueError(f"Unsupported artifact format: {artifact_format}")

    metadata = {
        "artifact_id": artifact_id,
        "format": artifact_format,
        "filename": filename,
        "media_type": media_type,
        "storage_path": str(content_path),
        "created_at_utc": created_at.isoformat(),
        "expires_at_utc": expires_at.isoformat(),
    }
    _metadata_path(artifact_id, artifact_dir=artifact_dir).write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def get_artifact_metadata(artifact_id: str, *, artifact_dir: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    _validate_artifact_id(artifact_id)
    metadata_file = _metadata_path(artifact_id, artifact_dir=artifact_dir)
    if not metadata_file.exists():
        raise ArtifactNotFoundError(f"Artifact '{artifact_id}' was not found")
    return json.loads(metadata_file.read_text(encoding="utf-8"))


def artifact_is_expired(metadata: dict[str, Any], *, now: datetime | None = None) -> bool:
    current = now or datetime.now(timezone.utc)
    try:
        expires_at = datetime.fromisoformat(str(metadata["expires_at_utc"]))
    except (KeyError, ValueError):
        return False
    return current >= expires_at


def delete_artifact(artifact_id: str, *, artifact_dir: str | os.PathLike[str] | None = None) -> None:
    _validate_artifact_id(artifact_id)
    metadata_file = _metadata_path(artifact_id, artifact_dir=artifact_dir)
    try:
        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        storage_path = Path(str(metadata.get("storage_path", "")))
        if storage_path.name:
            storage_path.unlink(missing_ok=True)
    except (OSError, json.JSONDecodeError):
        pass
    metadata_file.unlink(missing_ok=True)


def purge_expired_artifacts(
    *,
    artifact_dir: str | os.PathLike[str] | None = None,
    now: datetime | None = None,
) -> int:
    """Remove every expired artifact; returns how many were purged."""
    purged = 0
    for metadata_file in _resolve_root(artifact_dir).glob("*.json"):
        try:
            metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if artifact_is_expired(metadata, now=now):
            delete_artifact(metadata_file.stem, artifact_dir=artifact_dir)
            purged += 1
    return purged
