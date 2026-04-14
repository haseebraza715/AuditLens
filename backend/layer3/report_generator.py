from __future__ import annotations

import base64
import io
from datetime import datetime, timezone
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from backend.layer3.visualizations import (
    build_class_distribution_chart,
    build_correlation_heatmap,
    build_demographic_parity_chart,
    build_issue_type_chart,
    build_missingness_heatmap,
    build_severity_summary_chart,
)


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


def _reproducibility_payload(final_report: dict[str, Any]) -> dict[str, Any]:
    reproducibility = final_report.get("reproducibility", {}) or {}
    thresholds = reproducibility.get("severity_thresholds", {}) or {}
    return {
        "generated_at_utc": _safe_text(reproducibility.get("generated_at_utc", "")),
        "request_id": _safe_text(reproducibility.get("request_id", "")),
        "layer2_provider": _safe_text(reproducibility.get("layer2_provider", "unknown")),
        "layer2_model": _safe_text(reproducibility.get("layer2_model", "unknown")),
        "severity_thresholds": thresholds if isinstance(thresholds, dict) else {},
    }


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
    reproducibility = _reproducibility_payload(final_report)

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

    lines.append("## Reproducibility")
    lines.append("")
    lines.append(f"- Generated at (UTC): `{reproducibility['generated_at_utc'] or issued_at.isoformat()}`")
    lines.append(f"- Request ID: `{reproducibility['request_id'] or 'n/a'}`")
    lines.append(f"- Layer 2 provider: `{reproducibility['layer2_provider']}`")
    lines.append(f"- Layer 2 model: `{reproducibility['layer2_model']}`")
    threshold_items = reproducibility["severity_thresholds"].items()
    if threshold_items:
        lines.append("- Severity thresholds:")
        for metric, bounds in threshold_items:
            medium = _safe_text((bounds or {}).get("medium", ""))
            high = _safe_text((bounds or {}).get("high", ""))
            lines.append(f"  - `{metric}`: medium=`{medium}`, high=`{high}`")
    else:
        lines.append("- Severity thresholds: _Not available_")
    lines.append("")

    return "\n".join(lines).strip() + "\n"


def build_pdf_report(
    *,
    final_report: dict[str, Any],
    layer1_report: dict[str, Any] | None = None,
    generated_at_utc: datetime | None = None,
) -> bytes:
    issued_at = generated_at_utc or datetime.now(timezone.utc)
    task_context = final_report.get("task_context", {}) or {}
    issues = list(final_report.get("issues", []) or [])
    summary = _safe_text(final_report.get("summary", ""))
    disclaimer = _safe_text(final_report.get("disclaimer", ""))
    reproducibility = _reproducibility_payload(final_report)

    severity_chart = build_severity_summary_chart(layer1_report)
    issue_type_chart = build_issue_type_chart(final_report)
    class_distribution_chart = build_class_distribution_chart(layer1_report)
    demographic_parity_chart = build_demographic_parity_chart(layer1_report)
    correlation_heatmap = build_correlation_heatmap(layer1_report)
    missingness_heatmap = build_missingness_heatmap(layer1_report)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=42, rightMargin=42, topMargin=42, bottomMargin=42)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("AuditLens Bias Audit Report", styles["Title"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"Generated (UTC): {issued_at.isoformat()}", styles["Normal"]))
    story.append(Paragraph(f"Total issues: {len(issues)}", styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Task Description", styles["Heading2"]))
    story.append(Paragraph(_safe_text(final_report.get("task_description", "")) or "Not provided.", styles["Normal"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Executive Summary", styles["Heading2"]))
    story.append(Paragraph(summary or "No summary generated.", styles["Normal"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Task Context", styles["Heading2"]))
    task_rows = [
        ["Task type", _safe_text(task_context.get("task_type", "unknown"))],
        ["Stakes level", _safe_text(task_context.get("stakes_level", "unknown"))],
        ["Affected population", _safe_text(task_context.get("affected_population", "unknown"))],
        ["Decision impact", _safe_text(task_context.get("decision_impact", "unknown"))],
    ]
    task_table = Table(task_rows, colWidths=[1.8 * inch, 4.9 * inch])
    task_table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.7, colors.grey),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
                ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(task_table)
    story.append(Spacer(1, 12))

    story.append(Paragraph("Charts", styles["Heading2"]))
    story.append(Image(io.BytesIO(severity_chart), width=5.6 * inch, height=3.0 * inch))
    story.append(Spacer(1, 8))
    story.append(Image(io.BytesIO(issue_type_chart), width=5.8 * inch, height=3.1 * inch))
    story.append(Spacer(1, 8))
    story.append(Image(io.BytesIO(class_distribution_chart), width=5.8 * inch, height=3.1 * inch))
    story.append(Spacer(1, 8))
    story.append(Image(io.BytesIO(demographic_parity_chart), width=5.8 * inch, height=3.1 * inch))
    story.append(Spacer(1, 8))
    story.append(Image(io.BytesIO(correlation_heatmap), width=5.8 * inch, height=2.7 * inch))
    story.append(Spacer(1, 8))
    story.append(Image(io.BytesIO(missingness_heatmap), width=5.8 * inch, height=3.0 * inch))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Findings", styles["Heading2"]))
    if not issues:
        story.append(Paragraph("No issues were included in this report.", styles["Normal"]))
    else:
        for index, issue_entry in enumerate(issues, start=1):
            statistical = issue_entry.get("statistical_issue", {}) or {}
            interpretation = issue_entry.get("interpretation", {}) or {}
            mitigations = list(issue_entry.get("mitigations", []) or [])

            issue_title = _safe_text(statistical.get("type", "dataset_issue")).replace("_", " ").title()
            story.append(Paragraph(f"{index}. {issue_title}", styles["Heading3"]))
            story.append(
                Paragraph(
                    f"Severity: {_safe_text(statistical.get('severity', 'low')).upper()} | "
                    f"Issue ID: {_safe_text(statistical.get('issue_id', f'issue_{index}'))}",
                    styles["Normal"],
                )
            )
            story.append(Paragraph(_safe_text(statistical.get("description", "")), styles["Normal"]))
            story.append(Spacer(1, 4))
            story.append(Paragraph("Interpretation:", styles["BodyText"]))
            story.append(
                Paragraph(_safe_text(interpretation.get("why_harmful", "No interpretation provided.")), styles["Normal"])
            )
            story.append(
                Paragraph(
                    f"Likely impact: {_safe_text(interpretation.get('likely_model_impact', ''))}",
                    styles["Normal"],
                )
            )

            if mitigations:
                story.append(Paragraph("Mitigations:", styles["BodyText"]))
                for mitigation in mitigations[:3]:
                    story.append(
                        Paragraph(
                            f"- {_safe_text(mitigation.get('title', 'Mitigation'))} "
                            f"({_safe_text(mitigation.get('difficulty', 'medium'))})",
                            styles["Normal"],
                        )
                    )
            story.append(Spacer(1, 8))

    story.append(Paragraph("Disclaimer", styles["Heading2"]))
    story.append(
        Paragraph(
            disclaimer or "Human review is strongly recommended before deployment decisions.",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 10))
    story.append(Paragraph("Reproducibility", styles["Heading2"]))
    story.append(
        Paragraph(
            f"Generated at (UTC): {reproducibility['generated_at_utc'] or issued_at.isoformat()}",
            styles["Normal"],
        )
    )
    story.append(Paragraph(f"Request ID: {reproducibility['request_id'] or 'n/a'}", styles["Normal"]))
    story.append(Paragraph(f"Layer 2 provider: {reproducibility['layer2_provider']}", styles["Normal"]))
    story.append(Paragraph(f"Layer 2 model: {reproducibility['layer2_model']}", styles["Normal"]))
    threshold_items = reproducibility["severity_thresholds"].items()
    if threshold_items:
        for metric, bounds in threshold_items:
            medium = _safe_text((bounds or {}).get("medium", ""))
            high = _safe_text((bounds or {}).get("high", ""))
            story.append(Paragraph(f"- {metric}: medium={medium}, high={high}", styles["Normal"]))
    else:
        story.append(Paragraph("Severity thresholds: not available.", styles["Normal"]))

    doc.build(story)
    return buffer.getvalue()


def encode_pdf_base64(pdf_bytes: bytes) -> str:
    return base64.b64encode(pdf_bytes).decode("ascii")
