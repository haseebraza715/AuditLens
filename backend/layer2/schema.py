from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class TaskContext(BaseModel):
    task_type: Literal["binary_classification", "multiclass_classification", "regression", "unknown"] = (
        "unknown"
    )
    positive_class_meaning: str = ""
    affected_population: str = ""
    false_positive_consequence: str = ""
    false_negative_consequence: str = ""
    decision_impact: str = ""
    stakes_level: Literal["low", "medium", "high", "unknown"] = "unknown"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    assumptions: list[str] = Field(default_factory=list)


class IssueInterpretation(BaseModel):
    issue_id: str
    why_harmful: str
    at_risk_groups: list[str] = Field(default_factory=list)
    likely_model_impact: str
    severity_delta: Literal["higher", "equal", "lower"] = "equal"
    severity_rationale: str


class MitigationRecommendation(BaseModel):
    title: str
    category: str
    when_to_use: str
    tradeoffs: str
    difficulty: Literal["easy", "medium", "hard"]
    expected_impact: str
    code_snippet: str


class Layer2IssueReport(BaseModel):
    statistical_issue: dict[str, Any]
    interpretation: IssueInterpretation
    mitigations: list[MitigationRecommendation] = Field(default_factory=list)


class Layer2Report(BaseModel):
    task_description: str
    task_context: TaskContext
    issues: list[Layer2IssueReport]
    summary: str
    disclaimer: str
