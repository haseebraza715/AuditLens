from __future__ import annotations

import io
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pandas.errors import EmptyDataError, ParserError

from backend.layer1.audit import run_layer1_audit
from backend.utils.schema import AuditReport, UploadPreview

router = APIRouter()


def _normalize_sensitive_columns(raw_values: list[str]) -> list[str]:
    normalized: list[str] = []
    for raw in raw_values:
        for piece in raw.split(","):
            cleaned = piece.strip()
            if cleaned and cleaned not in normalized:
                normalized.append(cleaned)
    return normalized


def _read_csv_from_upload(file: UploadFile) -> pd.DataFrame:
    try:
        raw_bytes = file.file.read()
        if not raw_bytes:
            raise HTTPException(status_code=422, detail="Uploaded CSV is empty")
        return pd.read_csv(io.BytesIO(raw_bytes))
    except (ParserError, EmptyDataError):
        raise HTTPException(status_code=422, detail="Malformed CSV file")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/upload", response_model=UploadPreview)
def upload_preview(file: Annotated[UploadFile, File(...)]) -> UploadPreview:
    df = _read_csv_from_upload(file)
    return UploadPreview(rows=int(len(df)), columns=int(df.shape[1]), column_names=list(df.columns))


@router.post("/analyze", response_model=AuditReport)
def analyze(
    file: Annotated[UploadFile, File(...)],
    target_column: Annotated[str, Form(...)],
    sensitive_columns: Annotated[list[str], Form(...)],
) -> AuditReport:
    df = _read_csv_from_upload(file)

    normalized_sensitive = _normalize_sensitive_columns(sensitive_columns)
    if not normalized_sensitive:
        raise HTTPException(status_code=422, detail="sensitive_columns must not be empty")

    if target_column not in df.columns:
        raise HTTPException(
            status_code=422,
            detail=f"target_column '{target_column}' not found in CSV columns",
        )

    missing_sensitive = [col for col in normalized_sensitive if col not in df.columns]
    if missing_sensitive:
        raise HTTPException(
            status_code=422,
            detail=f"sensitive_columns not found in CSV columns: {missing_sensitive}",
        )

    report = run_layer1_audit(df, target_column, normalized_sensitive)
    return AuditReport.model_validate(report)
