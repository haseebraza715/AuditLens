from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd

from auditlens.core.audit import run_layer1_audit
from auditlens.core.schema import AuditIssue, AuditReport
from auditlens.exceptions import Layer2ConfigurationError, Layer2InvalidResponseError, Layer2ProviderError
from auditlens.interpretation.schema import Layer2Report
from auditlens.reporting.generator import build_markdown_report, build_pdf_report


def _layer1_payload_for_models(layer1_report: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in layer1_report.items() if k != "severity_thresholds"}


def _markdown_layer1_only(layer1_report: dict[str, Any]) -> str:
    info = layer1_report.get("dataset_info", {}) or {}
    summary = layer1_report.get("summary", {}) or {}
    issues = list(layer1_report.get("issues", []) or [])
    lines = [
        "# AuditLens statistical audit (Layer 1)",
        "",
        f"- Rows: `{info.get('rows', 0)}`",
        f"- Columns: `{info.get('columns', 0)}`",
        f"- Target: `{info.get('target_column', '')}`",
        f"- Sensitive columns: `{', '.join(info.get('sensitive_columns', []))}`",
        "",
        "## Summary",
        "",
        f"- Total issues: `{summary.get('total_issues', 0)}`",
        f"- High severity: `{summary.get('high_severity', 0)}`",
        f"- Medium severity: `{summary.get('medium_severity', 0)}`",
        f"- Low severity: `{summary.get('low_severity', 0)}`",
        "",
        "## Findings",
        "",
    ]
    if not issues:
        lines.append("_No issues detected by Layer 1 checks._")
    else:
        for idx, issue in enumerate(issues, start=1):
            lines.append(f"### {idx}. `{issue.get('issue_id', '')}` ({issue.get('type', '')})")
            lines.append("")
            lines.append(f"- Severity: **{str(issue.get('severity', '')).upper()}**")
            lines.append(f"- {issue.get('description', '')}")
            lines.append("")
    lines.append("")
    lines.append("_Layer 2 interpretation was not run. Pass `task_description` to enable LLM-assisted reporting._")
    lines.append("")
    return "\n".join(lines)


@dataclass
class AuditLensReport:
    """Result of `audit()` with Layer 1 statistics and optional Layer 2 interpretation."""

    _layer1_report: dict[str, Any]
    _interpretation: dict[str, Any] | None = None

    @property
    def summary(self) -> dict[str, Any]:
        return dict(self._layer1_report.get("summary", {}))

    @property
    def issues(self) -> list[AuditIssue]:
        return [AuditIssue.model_validate(item) for item in self._layer1_report.get("issues", [])]

    @property
    def layer1_report(self) -> AuditReport:
        return AuditReport.model_validate(_layer1_payload_for_models(self._layer1_report))

    @property
    def status(self) -> str | None:
        if self._interpretation is None:
            return None
        return str(self._interpretation.get("status"))

    @property
    def final_report(self) -> Layer2Report | None:
        if not self._interpretation or self._interpretation.get("status") != "complete":
            return None
        payload = self._interpretation.get("final_report") or {}
        return Layer2Report.model_validate(payload)

    @property
    def clarifying_questions(self) -> list[str] | None:
        if not self._interpretation or self._interpretation.get("status") != "needs_clarification":
            return None
        return list(self._interpretation.get("clarifying_questions", []))

    def to_markdown(self, *, generated_at_utc: datetime | None = None) -> str:
        if self._interpretation and self._interpretation.get("status") == "complete":
            final = self._interpretation.get("final_report") or {}
            return build_markdown_report(
                final_report=final,
                layer1_report=_layer1_payload_for_models(self._layer1_report),
                generated_at_utc=generated_at_utc,
            )
        return _markdown_layer1_only(self._layer1_report)

    def to_pdf(self, path: str, *, generated_at_utc: datetime | None = None) -> None:
        if not self._interpretation or self._interpretation.get("status") != "complete":
            raise ValueError(
                "PDF export requires a completed Layer 2 report. "
                "Provide a non-empty `task_description` and valid LLM configuration, "
                "or pass `llm_client` with a working `BaseLLMClient` implementation."
            )
        final = self._interpretation.get("final_report") or {}
        pdf_bytes = build_pdf_report(
            final_report=final,
            layer1_report=_layer1_payload_for_models(self._layer1_report),
            generated_at_utc=generated_at_utc,
        )
        with open(path, "wb") as handle:
            handle.write(pdf_bytes)


def audit(
    df: pd.DataFrame,
    *,
    target_col: str,
    sensitive_cols: list[str],
    task_description: str | None = None,
    llm_client: Any | None = None,
    severity_thresholds: dict[str, dict[str, float]] | None = None,
    clarification_answers: dict[str, Any] | None = None,
    request_id: str | None = None,
    layer2_provider: str | None = None,
    layer2_model: str | None = None,
    max_retries: int | None = None,
) -> AuditLensReport:
    """
    Run a bias audit: Layer 1 is always executed; Layer 2 runs when `task_description` is non-empty.

    When Layer 2 is enabled, configure a provider via environment variables or pass `llm_client`.
    """
    layer1_report = run_layer1_audit(
        df,
        target_col,
        sensitive_cols,
        severity_thresholds=severity_thresholds,
    )

    interpretation: dict[str, Any] | None = None
    if task_description is not None and str(task_description).strip():
        from auditlens.interpretation.pipeline import run_layer2_pipeline

        try:
            interpretation = run_layer2_pipeline(
                layer1_report=layer1_report,
                task_description=str(task_description).strip(),
                clarification_answers=clarification_answers,
                request_id=request_id,
                llm_client=llm_client,
                layer2_provider=layer2_provider,
                layer2_model=layer2_model,
                max_retries=max_retries,
            )
        except Layer2ConfigurationError:
            raise
        except Layer2InvalidResponseError:
            raise
        except Layer2ProviderError:
            raise

    return AuditLensReport(layer1_report, interpretation)
