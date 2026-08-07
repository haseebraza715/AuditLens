#!/usr/bin/env bash
# AuditLens — deterministic bias & data-quality audit demo.
#
# Runs FULLY OFFLINE: no network, no API keys, no LLM. Layer 1 statistical
# checks only. The markdown report and findings are deterministic given the
# bundled example CSV (byte-identical across runs); the optional PDF embeds a
# generation timestamp, so its bytes differ run-to-run even though the
# contents are the same.
#
# Usage:
#   ./scripts/demo.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PYTHON="$ROOT_DIR/.venv/bin/python"
EXAMPLE_CSV="$ROOT_DIR/examples/quickstart.csv"
OUT_DIR="$ROOT_DIR/demo-output"

if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "Missing virtualenv interpreter at .venv/bin/python" >&2
  echo "Set it up once with:" >&2
  echo "  python3 -m venv $ROOT_DIR/.venv" >&2
  echo "  $ROOT_DIR/.venv/bin/python -m pip install -e ." >&2
  exit 1
fi

if [[ ! -f "$EXAMPLE_CSV" ]]; then
  echo "Missing example dataset: $EXAMPLE_CSV" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"

export DEMO_ROOT="$ROOT_DIR"
export DEMO_CSV="$EXAMPLE_CSV"
export DEMO_OUT="$OUT_DIR"

# Strip any proxy vars so nothing attempts the network, and disable user-site
# packages so the demo runs against the project venv alone.
env \
  -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
  -u http_proxy -u https_proxy -u all_proxy \
  -u SOCKS_PROXY -u SOCKS5_PROXY \
  -u socks_proxy -u socks5_proxy \
  PYTHONNOUSERSITE=1 \
  "$VENV_PYTHON" -u - <<'PY'
from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from auditlens import audit

ROOT = Path(os.environ["DEMO_ROOT"])
CSV = Path(os.environ["DEMO_CSV"])
OUT = Path(os.environ["DEMO_OUT"])

COLOR = sys.stdout.isatty()


def c(code: str, s: str) -> str:
    return f"\x1b[{code}m{s}\x1b[0m" if COLOR else s


def bold(s: str) -> str:
    return c("1", s)


def dim(s: str) -> str:
    return c("2", s)


def green(s: str) -> str:
    return c("32;1", s)


def red(s: str) -> str:
    return c("31;1", s)


def yellow(s: str) -> str:
    return c("33;1", s)


def header(title: str, subtitle: str | None = None) -> None:
    width = 74
    print()
    print(bold("=" * width))
    print(bold(title))
    if subtitle:
        print(dim(subtitle))
    print(bold("=" * width))


def severity_badge(sev: str) -> str:
    if sev == "high":
        return red("HIGH")
    if sev == "medium":
        return yellow("MEDIUM")
    return dim("LOW")


WIDTH = 74
print()
print(bold("\u2550" * WIDTH))
print(bold("  AUDITLENS  \u2014  DETERMINISTIC BIAS & DATA-QUALITY AUDIT"))
print(dim("  Layer 1 statistical checks  \u00b7  fully offline  \u00b7  no API keys  \u00b7  markdown deterministic"))
print(bold("\u2550" * WIDTH))

# --- Step 1: load -----------------------------------------------------------
header("STEP 1  \u00b7  Load dataset")
df = pd.read_csv(CSV)
print(f"  file      : {CSV.relative_to(ROOT)}")
print(f"  rows      : {len(df)}")
print(f"  columns   : {', '.join(map(str, df.columns))}")
print(f"  target    : 'target'")
print(f"  sensitive : group, sex")

# --- Step 2: run the audit --------------------------------------------------
header("STEP 2  \u00b7  Run Layer 1 statistical audit")
print("  Checks applied:")
print("    \u2022 class distribution / imbalance")
print("    \u2022 differential missingness by group")
print("    \u2022 sensitive-column \u2194 target correlation")
print("    \u2022 subgroup label distribution (demographic parity)")
t0 = time.perf_counter()
report = audit(df, target_col="target", sensitive_cols=["group", "sex"])
elapsed = time.perf_counter() - t0
print()
print(f"  {green('\u2714')} audit() completed in {elapsed:.3f}s")

# --- Step 3: findings --------------------------------------------------------
header("STEP 3  \u00b7  Findings")
s = report.summary
total = s["total_issues"]
high = s["high_severity"]
medium = s["medium_severity"]
low = s["low_severity"]

bar = 22
print("  Severity summary")
print(f"    total : {total}")
print(f"    high  : {high:>2}  " + "\u2588" * (round(high / total * bar) if total else 0))
print(f"    med   : {medium:>2}  " + "\u2588" * (round(medium / total * bar) if total else 0))
print(f"    low   : {low:>2}  " + "\u2588" * (round(low / total * bar) if total else 0))

print()
print("  Detected issues")
print()
for i, issue in enumerate(report.issues, start=1):
    m = issue.metrics
    print(f"  {i}. {severity_badge(issue.severity)}  {issue.type}")
    print(f"      id     : {issue.issue_id}")
    print(f"      column : {issue.affected_column}")
    print(f"      detail : {issue.description}")
    if issue.type == "sensitive_correlation":
        val = abs(m.get("correlation_value", 0.0))
        print(f"      measure: {m.get('method', '?')} |r| = {val:.3f}   (n={m.get('sample_size', '?')})")
    elif issue.type == "demographic_parity_gap":
        rates = ", ".join(f"{k}={v:.2f}" for k, v in m.get("positive_rates", {}).items())
        print(f"      rates  : {rates}")
        print(
            f"      spread : {m.get('highest_positive_rate_group', '?')} leads "
            f"{m.get('lowest_positive_rate_group', '?')} by {m.get('demographic_parity_gap', 0.0):.3f}"
        )
    elif issue.type == "differential_missingness":
        rates = ", ".join(f"{k}={v:.2f}" for k, v in m.get("missingness_rates", {}).items())
        print(f"      missing: {rates}")
        print(
            f"      gap    : {m.get('highest_missing_group', '?')} missing "
            f"{m.get('missingness_gap', 0.0):.3f} more than {m.get('lowest_missing_group', '?')}"
        )
    elif issue.type == "class_imbalance":
        print(
            f"      class  : majority={m.get('majority_class', '?')} "
            f"({m.get('majority_count', '?')}) vs minority={m.get('minority_class', '?')} "
            f"({m.get('minority_count', '?')})"
        )
    print()

# --- Step 4: shareable report ------------------------------------------------
header("STEP 4  \u00b7  Shareable markdown report")
markdown = report.to_markdown()
print(dim("\u2500" * 72))
print(markdown)
print(dim("\u2500" * 72))

md_path = OUT / "quickstart-report.md"
md_path.write_text(markdown, encoding="utf-8")
print()
print(f"  {green('\u2714')} Markdown report saved \u2192 {md_path.relative_to(ROOT)}")

pdf_path = OUT / "quickstart-report.pdf"
try:
    from auditlens.reporting.generator import build_pdf_report

    snapshot = report.to_dict()
    issues = [
        {
            "statistical_issue": issue.model_dump(mode="python"),
            "interpretation": {},
            "mitigations": [],
        }
        for issue in report.issues
    ]
    final_report = {
        "task_description": "Layer 1 statistical bias & data-quality audit (no LLM)",
        "summary": (
            f"Deterministic statistical audit completed: {total} issue(s) "
            f"({high} high, {medium} medium, {low} low)."
        ),
        "task_context": {
            "task_type": "bias_audit",
            "stakes_level": "unknown",
            "affected_population": "Dataset under review",
            "decision_impact": "Under review",
        },
        "issues": issues,
        "disclaimer": (
            "Generated by AuditLens Layer 1 statistical checks only; "
            "no LLM interpretation was used. Human review is recommended before deployment decisions."
        ),
        "reproducibility": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "request_id": "demo",
            "layer2_provider": "none",
            "layer2_model": "none",
            "severity_thresholds": snapshot.get("severity_thresholds", {}),
        },
    }
    pdf_bytes = build_pdf_report(
        final_report=final_report,
        layer1_report=snapshot["layer1_report"],
        generated_at_utc=datetime.now(timezone.utc),
    )
    pdf_path.write_bytes(pdf_bytes)
    print(f"  {green('\u2714')} PDF report saved (pdf extra installed) \u2192 {pdf_path.relative_to(ROOT)}")
except ImportError:
    print(f"  {dim('\u00b7')} PDF skipped: 'pdf' extra not installed  (try: .venv/bin/python -m pip install -e '.[pdf]')")
except Exception as exc:  # pragma: no cover - defensive
    print(f"  {dim('\u00b7')} PDF skipped: {exc}")

print()
print(bold("  NEXT STEPS"))
print("    \u00b7 Use it in your own notebook:  from auditlens import audit")
print("    \u00b7 Enable Layer 2 LLM interpretation: pass task_description=...")
print("    \u00b7 Compare with the committed example: docs/examples/quickstart-result.md")
print()
PY
