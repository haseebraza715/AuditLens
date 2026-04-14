from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


class ArtifactNotFoundError(FileNotFoundError):
    pass


def _artifact_root() -> Path:
    configured = os.getenv("AUDITLENS_ARTIFACT_DIR", ".auditlens_artifacts").strip() or ".auditlens_artifacts"
    root = Path(configured)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _metadata_path(artifact_id: str) -> Path:
    return _artifact_root() / f"{artifact_id}.json"


def _content_path(artifact_id: str, extension: str) -> Path:
    return _artifact_root() / f"{artifact_id}.{extension}"


def save_report_artifact(
    *,
    artifact_format: str,
    filename: str,
    content: str,
    retention_hours: int = 168,
) -> dict[str, Any]:
    artifact_id = str(uuid4())
    created_at = datetime.now(timezone.utc)
    expires_at = created_at + timedelta(hours=max(retention_hours, 1))

    if artifact_format == "markdown":
        extension = "md"
        media_type = "text/markdown; charset=utf-8"
        content_path = _content_path(artifact_id, extension)
        content_path.write_text(content, encoding="utf-8")
    elif artifact_format == "pdf_base64":
        extension = "pdf"
        media_type = "application/pdf"
        content_bytes = base64.b64decode(content)
        content_path = _content_path(artifact_id, extension)
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
    _metadata_path(artifact_id).write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def get_artifact_metadata(artifact_id: str) -> dict[str, Any]:
    metadata_file = _metadata_path(artifact_id)
    if not metadata_file.exists():
        raise ArtifactNotFoundError(f"Artifact '{artifact_id}' was not found")
    return json.loads(metadata_file.read_text(encoding="utf-8"))

