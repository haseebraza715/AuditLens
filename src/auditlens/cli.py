"""Command-line interface for AuditLens.

Thin wrapper over the library pipeline: `auditlens audit` prints the Layer 1
findings table (deterministic, offline), `auditlens report` writes shareable
markdown/HTML/JSON artifacts into an output directory. No audit logic lives
here; everything delegates to `auditlens.audit` and the report wrappers.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

import pandas as pd

from auditlens import audit
from auditlens.exceptions import AuditLensError

_ANSI = {"reset": "\x1b[0m", "red": "\x1b[31;1m", "yellow": "\x1b[33;1m", "dim": "\x1b[2m"}


def _style(severity: str) -> str:
    """Colorize a severity label when stdout is a terminal (plain otherwise)."""
    if not sys.stdout.isatty():
        return severity.upper()
    color = {"high": "red", "medium": "yellow", "low": "dim"}.get(severity, "")
    code = _ANSI.get(color, "")
    return f"{code}{severity.upper()}{_ANSI['reset']}"


def _metric_detail(issue_type: str, metrics: dict[str, Any]) -> str:
    """One-line summary of the metric that triggered an issue."""
    if issue_type == "sensitive_correlation":
        method = metrics.get("method", "?")
        value = abs(float(metrics.get("correlation_value", 0.0)))
        return f"{method} |r| = {value:.3f} (n={metrics.get('sample_size', '?')})"
    if issue_type == "demographic_parity_gap":
        rates = ", ".join(
            f"{k}={v:.2f}" for k, v in (metrics.get("positive_rates", {}) or {}).items()
        )
        return f"gap = {metrics.get('demographic_parity_gap', 0.0):.3f} ({rates})"
    if issue_type == "differential_missingness":
        rates = ", ".join(
            f"{k}={v:.2f}" for k, v in (metrics.get("missingness_rates", {}) or {}).items()
        )
        return f"gap = {metrics.get('missingness_gap', 0.0):.3f} ({rates})"
    if issue_type == "class_imbalance":
        return (
            f"majority={metrics.get('majority_class', '?')} "
            f"({metrics.get('majority_count', '?')}) vs "
            f"minority={metrics.get('minority_class', '?')} "
            f"({metrics.get('minority_count', '?')})"
        )
    return json.dumps(metrics, default=str)[:80]


def _findings_table(report: Any) -> str:
    """Render the findings table: severity, type, affected column, description."""
    issues = report.issues
    rows = [[_style(i.severity), i.type, i.affected_column, i.description] for i in issues]
    headers = ["SEVERITY", "TYPE", "COLUMN", "DESCRIPTION"]
    widths = [len(h) for h in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(str(cell)))
    terminal = _terminal_width()
    if terminal:
        widths[3] = min(widths[3], max(20, terminal - sum(widths[:3]) - 9))
    lines = ["  " + "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))]
    lines.append("  " + "  ".join("-" * widths[i] for i in range(len(headers))))
    for idx, row in enumerate(rows, start=1):
        issue = issues[idx - 1]
        desc = str(row[3])
        if len(desc) > widths[3]:
            desc = desc[: widths[3] - 1] + "\u2026"
        cells = [_style(row[0]), row[1].ljust(widths[1]), row[2].ljust(widths[2]), desc]
        lines.append(f"{idx:>2} " + "  ".join(cells))
        detail = _metric_detail(issue.type, issue.metrics)
        lines.append(f"    metric: {detail}")
    return "\n".join(lines)


def _terminal_width() -> int | None:
    try:
        import shutil

        return shutil.get_terminal_size((120, 24)).columns
    except (ImportError, OSError):
        return None


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def _cmd_audit(args: argparse.Namespace) -> int:
    report = audit(
        _read_csv(Path(args.file)),
        target_col=args.target,
        sensitive_cols=list(args.sensitive),
    )
    summary = report.summary
    if args.format == "json":
        print(
            json.dumps(
                {
                    "summary": summary,
                    "dataset_info": report.layer1_report.dataset_info.model_dump(),
                    "issues": [i.model_dump(mode="json") for i in report.issues],
                },
                indent=2,
            )
        )
        return 0
    print(
        f"Dataset: {args.file}  ({report.layer1_report.dataset_info.rows} rows, "
        f"{report.layer1_report.dataset_info.columns} columns)"
    )
    print(
        f"Target: {args.target} | Sensitive: {', '.join(report.layer1_report.dataset_info.sensitive_columns)}"
    )
    total = summary["total_issues"]
    print(
        f"Summary: {total} issue(s) "
        f"[{_style('high')} {summary['high_severity']}, "
        f"{_style('medium')} {summary['medium_severity']}, "
        f"{_style('low')} {summary['low_severity']}]"
    )
    print()
    if total == 0:
        print("No issues detected by Layer 1 checks.")
    else:
        print(_findings_table(report))
    return 0


def _html_report(report: Any) -> str:
    """Minimal standalone HTML page built from the Layer 1 findings."""
    rows = []
    for issue in report.issues:
        desc = (issue.description or "")[:200]
        rows.append(
            "<tr>"
            f"<td><code>{_esc(str(issue.type))}</code></td>"
            f"<td><b>{_esc(str(issue.severity))}</b></td>"
            f"<td><code>{_esc(str(issue.affected_column))}</code></td>"
            f"<td>{_esc(desc)}</td>"
            "</tr>"
        )
    if not rows:
        rows.append("<tr><td colspan='4'><i>No issues detected by Layer 1.</i></td></tr>")
    s = report.summary
    header = (
        f"<h1>AuditLens bias audit report</h1>"
        f"<p>Total issues: <b>{s['total_issues']}</b> "
        f"(high {s['high_severity']}, medium {s['medium_severity']}, low {s['low_severity']})</p>"
    )
    table = (
        "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse'>"
        "<thead><tr><th>Type</th><th>Severity</th><th>Column</th><th>Description</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )
    return (
        "<!doctype html>\n<html><head><meta charset='utf-8'>"
        "<title>AuditLens bias audit report</title></head><body>"
        f"{header}{table}</body></html>\n"
    )


def _esc(value: str) -> str:
    import html

    return html.escape(value, quote=True)


def _write_artifact(path: Path, content: bytes) -> None:
    path.write_bytes(content)
    print(f"  wrote {path} ({len(content)} bytes)")


def _cmd_report(args: argparse.Namespace) -> int:
    report = audit(
        _read_csv(Path(args.file)),
        target_col=args.target,
        sensitive_cols=list(args.sensitive),
    )
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_artifact(out_dir / "report.md", report.to_markdown().encode("utf-8"))
    _write_artifact(out_dir / "report.json", json.dumps(report.to_dict(), indent=2).encode("utf-8"))
    _write_artifact(out_dir / "report.html", _html_report(report).encode("utf-8"))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="auditlens",
        description="Deterministic bias and fairness audit for tabular CSV data (offline, no LLM).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    audit_parser = sub.add_parser("audit", help="run the statistical audit and print findings")
    audit_parser.add_argument("file", help="path to the input CSV")
    audit_parser.add_argument("--sensitive", nargs="+", required=True, metavar="COL", help="sensitive column name(s)")
    audit_parser.add_argument("--target", required=True, help="target column name")
    audit_parser.add_argument("--format", choices=["table", "json"], default="table", help="output format (default: table)")
    audit_parser.set_defaults(func=_cmd_audit)

    report_parser = sub.add_parser("report", help="write shareable markdown/HTML/JSON report artifacts")
    report_parser.add_argument("file", help="path to the input CSV")
    report_parser.add_argument("--sensitive", nargs="+", required=True, metavar="COL", help="sensitive column name(s)")
    report_parser.add_argument("--target", required=True, help="target column name")
    report_parser.add_argument("-o", "--output", default=".", help="output directory (default: current directory)")
    report_parser.set_defaults(func=_cmd_report)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (AuditLensError, FileNotFoundError, OSError, ValueError, pd.errors.EmptyDataError, pd.errors.ParserError) as exc:
        print(f"auditlens: error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
