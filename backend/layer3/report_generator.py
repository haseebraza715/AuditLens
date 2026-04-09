from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _severity_badge(severity: str) -> str:
    level = (severity or "low").lower()
    if level == "high":
        return "HIGH"
    if level == "medium":
        return "MEDIUM"
    return "LOW"


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def build_markdown_report(
    *,
    final_report: dict[str, Any],
    layer1_report: dict[str, Any] | None = None,
    generated_at_utc: datetime | None = None,
) -> str:
    """
    Build a shareable markdown report from Layer 2 final output.
    """
    issued_at = generated_at_utc or datetime.now(timezone.utc)
    task_description = _safe_text(final_report.get("task_description", ""))
    summary = _safe_text(final_report.get("summary", ""))
    disclaimer = _safe_text(final_report.get("disclaimer", ""))
    task_context = final_report.get("task_context", {}) or {}
    issues = list(final_report.get("issues", []) or [])

    lines: list[str] = []
    lines.append("# AuditLens Bias Audit Report")
    lines.append("")
    lines.append(f"- Generated (UTC): `{issued_at.isoformat()}`")
    lines.append(f"- Total issues: `{len(issues)}`")
    lines.append("")

    lines.append("## Task Description")
    lines.append("")
    lines.append(task_description or "_Not provided_")
    lines.append("")

    lines.append("## Executive Summary")
    lines.append("")
    lines.append(summary or "_No summary generated._")
    lines.append("")

    lines.append("## Task Context")
    lines.append("")
    lines.append(f"- Task type: `{_safe_text(task_context.get('task_type', 'unknown'))}`")
    lines.append(f"- Stakes level: `{_safe_text(task_context.get('stakes_level', 'unknown'))}`")
    lines.append(f"- Affected population: {_safe_text(task_context.get('affected_population', 'unknown'))}")
    lines.append(f"- Decision impact: {_safe_text(task_context.get('decision_impact', 'unknown'))}")
    lines.append("")

    if layer1_report:
        dataset_info = layer1_report.get("dataset_info", {}) or {}
        lines.append("## Dataset Overview")
        lines.append("")
        lines.append(f"- Rows: `{dataset_info.get('rows', 0)}`")
        lines.append(f"- Columns: `{dataset_info.get('columns', 0)}`")
        lines.append(f"- Target column: `{dataset_info.get('target_column', '')}`")
        lines.append(
            f"- Sensitive columns: `{', '.join(dataset_info.get('sensitive_columns', []))}`"
        )
        lines.append("")

    lines.append("## Findings")
    lines.append("")
    if not issues:
        lines.append("_No issues were included in this report._")
        lines.append("")
    else:
        for idx, issue_entry in enumerate(issues, start=1):
            statistical = issue_entry.get("statistical_issue", {}) or {}
            interpretation = issue_entry.get("interpretation", {}) or {}
            mitigations = list(issue_entry.get("mitigations", []) or [])

            issue_id = _safe_text(statistical.get("issue_id", interpretation.get("issue_id", f"issue_{idx}")))
            issue_type = _safe_text(statistical.get("type", "dataset_issue")).replace("_", " ")
            severity = _severity_badge(_safe_text(statistical.get("severity", "low")))

            lines.append(f"### {idx}. {issue_type.title()} (`{issue_id}`)")
            lines.append("")
            lines.append(f"- Statistical severity: **{severity}**")
            lines.append(f"- Description: {_safe_text(statistical.get('description', ''))}")
            lines.append(
                f"- Task-adjusted severity delta: `{_safe_text(interpretation.get('severity_delta', 'equal'))}`"
            )
            lines.append("")
            lines.append("#### Interpretation")
            lines.append("")
            lines.append(_safe_text(interpretation.get("why_harmful", "")) or "_No interpretation provided._")
            lines.append("")
            lines.append(
                f"- Likely model impact: {_safe_text(interpretation.get('likely_model_impact', ''))}"
            )
            at_risk = interpretation.get("at_risk_groups", []) or []
            if at_risk:
                lines.append(f"- At-risk groups: `{', '.join(str(v) for v in at_risk)}`")
            lines.append(
                f"- Rationale: {_safe_text(interpretation.get('severity_rationale', ''))}"
            )
            lines.append("")
            lines.append("#### Mitigations")
            lines.append("")
            if not mitigations:
                lines.append("_No mitigation recommendations provided._")
                lines.append("")
            else:
                for mitigation in mitigations:
                    lines.append(
                        f"- **{_safe_text(mitigation.get('title', 'Mitigation'))}** "
                        f"(`{_safe_text(mitigation.get('difficulty', 'medium'))}`)"
                    )
                    lines.append(f"  - Category: `{_safe_text(mitigation.get('category', 'general'))}`")
                    lines.append(f"  - When to use: {_safe_text(mitigation.get('when_to_use', ''))}")
                    lines.append(f"  - Tradeoffs: {_safe_text(mitigation.get('tradeoffs', ''))}")
                    lines.append(
                        f"  - Expected impact: {_safe_text(mitigation.get('expected_impact', ''))}"
                    )
                    code = _safe_text(mitigation.get("code_snippet", ""))
                    if code:
                        lines.append("")
                        lines.append("```python")
                        lines.append(code)
                        lines.append("```")
                    lines.append("")

    lines.append("## Disclaimer")
    lines.append("")
    lines.append(disclaimer or "Human review is strongly recommended before deployment decisions.")
    lines.append("")

    return "\n".join(lines).strip() + "\n"
