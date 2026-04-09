from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class DatasetInfo(BaseModel):
    rows: int = Field(..., ge=0)
    columns: int = Field(..., ge=0)
    target_column: str
    sensitive_columns: list[str]


class AuditIssue(BaseModel):
    issue_id: str
    type: str
    description: str
    affected_column: str
    severity: Literal["high", "medium", "low"]
    metrics: dict[str, Any]
    justification: str


class AuditSummary(BaseModel):
    total_issues: int = Field(..., ge=0)
    high_severity: int = Field(..., ge=0)
    medium_severity: int = Field(..., ge=0)
    low_severity: int = Field(..., ge=0)


class AuditReport(BaseModel):
    dataset_info: DatasetInfo
    issues: list[AuditIssue]
    summary: AuditSummary


class UploadPreview(BaseModel):
    rows: int = Field(..., ge=0)
    columns: int = Field(..., ge=0)
    column_names: list[str]
