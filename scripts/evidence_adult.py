#!/usr/bin/env python3
"""AuditLens evidence artifact generator: UCI Adult (Census Income).

Runs the deterministic Layer 1 statistical audit on the vendored public UCI
Adult dataset and writes byte-stable evidence artifacts under docs/evidence/.

* No network, no API keys, no LLM: Layer 1 statistics only.
* Input: tests/fixtures/adult.data (schema pinned below; SHA-256 verified).
* Outputs:
    docs/evidence/adult-income-report.json  JSON snapshot (floats rounded to 6 dp)
    docs/evidence/adult-income-report.md    human-readable markdown + provenance
* Determinism: no timestamps, no randomness. Same input -> same bytes.

Dataset provenance and license
------------------------------
Source: UCI Machine Learning Repository, "Adult" (Census Income) data set.
  https://archive.ics.uci.edu/dataset/2/adult
The data was extracted from the 1994 US Census Bureau database. UCI licenses
the dataset under Creative Commons Attribution 4.0 International (CC BY 4.0).
The vendored copy is tests/fixtures/adult.data (32,561
rows, missing values encoded as "?"), SHA-256:
5b00264637dbfec36bdeaab5676b0b309ff9eb788d63554ca0a249491c86603d

Usage:
    .venv/bin/python scripts/evidence_adult.py
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

from auditlens import audit

REPO_ROOT = Path(__file__).resolve().parents[1]

EXPECTED_SHA256 = "5b00264637dbfec36bdeaab5676b0b309ff9eb788d63554ca0a249491c86603d"
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "adult.data"
OUT_DIR = REPO_ROOT / "docs" / "evidence"

TARGET_COL = "income"
SENSITIVE_COLS = ["sex", "race"]

ADULT_COLUMNS = [
    "age",
    "workclass",
    "fnlwgt",
    "education",
    "education_num",
    "marital_status",
    "occupation",
    "relationship",
    "race",
    "sex",
    "capital_gain",
    "capital_loss",
    "hours_per_week",
    "native_country",
    "income",
]

SOURCE_URL = "https://archive.ics.uci.edu/dataset/2/adult"
LICENSE_NOTE = (
    "Creative Commons Attribution 4.0 International (CC BY 4.0). Cite Becker & Kohavi (1996), DOI 10.24432/C5XW20."
)
FLOAT_ROUND = 6
EVIDENCE_FORMAT = "adult-layer1-v1"


def load_adult(path: Path | None = None) -> pd.DataFrame:
    path = Path(path) if path is not None else FIXTURE_PATH
    return pd.read_csv(
        path,
        header=None,
        names=ADULT_COLUMNS,
        skipinitialspace=True,
        na_values="?",
    )


def fixture_sha256(path: Path | None = None) -> str:
    path = Path(path) if path is not None else FIXTURE_PATH
    return hashlib.sha256(path.read_bytes()).hexdigest()


def round_floats(value: Any) -> Any:
    """Recursively round floats to FLOAT_ROUND decimals.

    Full-precision floats depend on the exact scipy/pandas/numpy build, so
    rounding makes the committed artifact byte-stable across environments.
    Non-finite floats would be an instability in the pipeline and are rejected.
    """
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"non-finite float in evidence payload: {value!r}")
        return round(value, FLOAT_ROUND)
    if isinstance(value, dict):
        return {str(k): round_floats(v) for k, v in value.items()}
    if isinstance(value, list):
        return [round_floats(v) for v in value]
    if isinstance(value, tuple):
        return [round_floats(v) for v in value]
    return value


def report_to_json(report: Any) -> str:
    payload = round_floats(report.to_dict())
    return json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True) + "\n"


def build_markdown(report: Any, sha256: str, rows: int) -> str:
    """Static, byte-stable markdown: provenance header + report.to_markdown()."""
    header = "\n".join(
        [
            "# AuditLens evidence: UCI Adult (Census Income), Layer 1 statistical audit",
            "",
            "Deterministic Layer 1 audit. No LLM, no network, no API keys.",
            "",
            "## Dataset",
            "",
            "- Source: UCI Machine Learning Repository, 'Adult' (Census Income)",
            f"- URL: {SOURCE_URL}",
            f"- License: {LICENSE_NOTE}",
            f"- Rows: {rows}",
            f"- Fixture SHA-256: `{sha256}`",
            f"- Target: `{TARGET_COL}` (`<=50K` / `>50K`)",
            f"- Sensitive columns: `{', '.join(SENSITIVE_COLS)}`",
            f"- Columns: {', '.join(ADULT_COLUMNS)}",
            f"- Evidence format: `{EVIDENCE_FORMAT}`",
            "",
            "## Interpretation boundary",
            "",
            "These findings are **effect-size screening signals**, not significance",
            "tests and not evidence of causality. Layer 1 runs no hypothesis tests",
            "and no confidence intervals; severity is a fixed magnitude cutoff",
            "(`SEVERITY_THRESHOLDS`). With some sensitive subgroups the underlying",
            "sample sizes are small, so estimates carry sampling error. Validate on",
            "task-specific data before drawing conclusions.",
            "",
            "## Regeneration",
            "",
            "    .venv/bin/python scripts/evidence_adult.py",
            "",
            "The JSON artifact rounds floats to 6 decimal places for cross-version",
            "byte stability; the markdown body below is exactly `report.to_markdown()`.",
            "",
            "---",
            "",
        ]
    )
    return header + report.to_markdown()


def main() -> None:
    sha256 = fixture_sha256()
    if sha256 != EXPECTED_SHA256:
        raise SystemExit(f"fixture SHA-256 mismatch: expected {EXPECTED_SHA256}, got {sha256}")

    df = load_adult()
    report = audit(df, target_col=TARGET_COL, sensitive_cols=SENSITIVE_COLS)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / "adult-income-report.json"
    md_path = OUT_DIR / "adult-income-report.md"
    json_path.write_text(report_to_json(report), encoding="utf-8")
    md_path.write_text(build_markdown(report, sha256, len(df)), encoding="utf-8")

    print(f"wrote {json_path.relative_to(REPO_ROOT)} ({json_path.stat().st_size} bytes)")
    print(f"wrote {md_path.relative_to(REPO_ROOT)} ({md_path.stat().st_size} bytes)")
    print(f"summary: {report.summary}")
    print(f"issue order: {[i.issue_id for i in report.issues]}")


if __name__ == "__main__":
    main()
