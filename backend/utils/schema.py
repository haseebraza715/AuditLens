from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field

from backend.layer2.schema import (
    IssueInterpretation,
    Layer2IssueReport,
    Layer2Report,
    MitigationRecommendation,
    TaskContext,
)


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


class AnalyzeTaskNeedsClarification(BaseModel):
    status: Literal["needs_clarification"]
    clarifying_questions: list[str]
    task_context_partial: dict[str, Any]
    layer1_report: AuditReport


class AnalyzeTaskComplete(BaseModel):
    status: Literal["complete"]
    final_report: Layer2Report


class ReportArtifact(BaseModel):
    format: Literal["markdown", "pdf_base64"]
    filename: str
    content: str


class AnalyzeTaskReportNeedsClarification(BaseModel):
    status: Literal["needs_clarification"]
    clarifying_questions: list[str]
    task_context_partial: dict[str, Any]
    layer1_report: AuditReport


class AnalyzeTaskReportComplete(BaseModel):
    status: Literal["complete"]
    final_report: Layer2Report
    report_artifact: ReportArtifact


AnalyzeTaskResponse = Annotated[
    Union[AnalyzeTaskNeedsClarification, AnalyzeTaskComplete],
    Field(discriminator="status"),
]


AnalyzeTaskReportResponse = Annotated[
    Union[AnalyzeTaskReportNeedsClarification, AnalyzeTaskReportComplete],
    Field(discriminator="status"),
]


__all__ = [
    "DatasetInfo",
    "AuditIssue",
    "AuditSummary",
    "AuditReport",
    "UploadPreview",
    "TaskContext",
    "IssueInterpretation",
    "MitigationRecommendation",
    "Layer2IssueReport",
    "Layer2Report",
    "AnalyzeTaskNeedsClarification",
    "AnalyzeTaskComplete",
    "AnalyzeTaskResponse",
    "ReportArtifact",
    "AnalyzeTaskReportNeedsClarification",
    "AnalyzeTaskReportComplete",
    "AnalyzeTaskReportResponse",
]
