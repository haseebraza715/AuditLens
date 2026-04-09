from __future__ import annotations

import io
import json
from json import JSONDecodeError
from typing import Annotated, Optional
from uuid import uuid4

import pandas as pd
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pandas.errors import EmptyDataError, ParserError

from backend.layer2.agent import run_layer2_pipeline
from backend.layer2.errors import Layer2InvalidResponseError, Layer2ProviderError
from backend.layer3.report_generator import build_markdown_report
from backend.utils.config import Layer2ConfigurationError, get_layer2_settings
from backend.layer1.audit import run_layer1_audit
from backend.utils.schema import AnalyzeTaskReportResponse, AnalyzeTaskResponse, AuditReport, UploadPreview

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


def _parse_optional_json(raw_json: str) -> dict[str, object]:
    try:
        parsed = json.loads(raw_json)
    except JSONDecodeError:
        raise HTTPException(status_code=422, detail="clarification_answers must be valid JSON")
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=422, detail="clarification_answers must be a JSON object")
    return parsed


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


@router.post("/analyze-task", response_model=AnalyzeTaskResponse)
def analyze_task(
    file: Annotated[UploadFile, File(...)],
    target_column: Annotated[str, Form(...)],
    sensitive_columns: Annotated[list[str], Form(...)],
    task_description: Annotated[str, Form(...)],
    clarification_answers: Annotated[Optional[str], Form()] = None,
) -> AnalyzeTaskResponse:
    df = _read_csv_from_upload(file)

    normalized_sensitive = _normalize_sensitive_columns(sensitive_columns)
    if not normalized_sensitive:
        raise HTTPException(status_code=422, detail="sensitive_columns must not be empty")

    if not task_description.strip():
        raise HTTPException(status_code=422, detail="task_description must not be empty")

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

    clarification_payload = None
    if clarification_answers:
        clarification_payload = _parse_optional_json(clarification_answers)

    try:
        settings = get_layer2_settings()
        if len(task_description) > settings.max_task_description_chars:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"task_description exceeds {settings.max_task_description_chars} characters"
                ),
            )
    except Layer2ConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    layer1_report = run_layer1_audit(df, target_column, normalized_sensitive)

    try:
        result = run_layer2_pipeline(
            layer1_report=layer1_report,
            task_description=task_description.strip(),
            clarification_answers=clarification_payload,
            request_id=str(uuid4()),
        )
    except Layer2ConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Layer2InvalidResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Layer2ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return result  # type: ignore[return-value]


@router.post("/analyze-task-report", response_model=AnalyzeTaskReportResponse)
def analyze_task_report(
    file: Annotated[UploadFile, File(...)],
    target_column: Annotated[str, Form(...)],
    sensitive_columns: Annotated[list[str], Form(...)],
    task_description: Annotated[str, Form(...)],
    clarification_answers: Annotated[Optional[str], Form()] = None,
) -> AnalyzeTaskReportResponse:
    df = _read_csv_from_upload(file)

    normalized_sensitive = _normalize_sensitive_columns(sensitive_columns)
    if not normalized_sensitive:
        raise HTTPException(status_code=422, detail="sensitive_columns must not be empty")

    if not task_description.strip():
        raise HTTPException(status_code=422, detail="task_description must not be empty")

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

    clarification_payload = None
    if clarification_answers:
        clarification_payload = _parse_optional_json(clarification_answers)

    try:
        settings = get_layer2_settings()
        if len(task_description) > settings.max_task_description_chars:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"task_description exceeds {settings.max_task_description_chars} characters"
                ),
            )
    except Layer2ConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    layer1_report = run_layer1_audit(df, target_column, normalized_sensitive)

    try:
        result = run_layer2_pipeline(
            layer1_report=layer1_report,
            task_description=task_description.strip(),
            clarification_answers=clarification_payload,
            request_id=str(uuid4()),
        )
    except Layer2ConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Layer2InvalidResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Layer2ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    if result.get("status") == "needs_clarification":
        return result  # type: ignore[return-value]

    final_report = result.get("final_report", {})
    markdown_content = build_markdown_report(
        final_report=final_report,
        layer1_report=layer1_report,
    )

    return {
        "status": "complete",
        "final_report": final_report,
        "report_artifact": {
            "format": "markdown",
            "filename": "auditlens_report.md",
            "content": markdown_content,
        },
    }
