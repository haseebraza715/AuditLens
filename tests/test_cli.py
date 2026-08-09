from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from auditlens.cli import main

QUICKSTART = Path(__file__).resolve().parents[1] / "examples" / "quickstart.csv"

BALANCED_CSV = "group,target\nA,0\nA,1\nB,0\nB,1\n"


def _write_csv(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "data.csv"
    path.write_text(content, encoding="utf-8")
    return path


def test_audit_table_output(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["audit", str(QUICKSTART), "--sensitive", "group", "sex", "--target", "target"]) == 0
    out = capsys.readouterr().out
    assert "Summary: 2 issue(s)" in out
    assert "sensitive_correlation" in out
    assert "demographic_parity_gap" in out
    assert "point_biserial |r| = 0.500" in out
    assert "SEVERITY" in out


def test_audit_json_output(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["audit", str(QUICKSTART), "--sensitive", "sex", "--target", "target", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["total_issues"] == 2
    assert payload["dataset_info"]["rows"] == 8
    assert [i["type"] for i in payload["issues"]] == ["sensitive_correlation", "demographic_parity_gap"]


def test_audit_no_issues(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    csv_path = _write_csv(tmp_path, BALANCED_CSV)
    assert main(["audit", str(csv_path), "--sensitive", "group", "--target", "target"]) == 0
    out = capsys.readouterr().out
    assert "0 issue(s)" in out
    assert "No issues detected" in out


def test_audit_missing_file_exit_code(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    missing = tmp_path / "missing.csv"
    assert main(["audit", str(missing), "--sensitive", "group", "--target", "target"]) == 1
    assert "error" in capsys.readouterr().err


def test_audit_target_in_sensitive_exit_code(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["audit", str(QUICKSTART), "--sensitive", "target", "--target", "target"]) == 1
    assert "must not also be listed" in capsys.readouterr().err


def test_audit_unknown_column_exit_code(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["audit", str(QUICKSTART), "--sensitive", "nope", "--target", "target"]) == 1
    assert "not found" in capsys.readouterr().err


def test_audit_empty_csv_exit_code(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    csv_path = _write_csv(tmp_path, "")
    assert main(["audit", str(csv_path), "--sensitive", "group", "--target", "target"]) == 1
    assert "error" in capsys.readouterr().err


def test_missing_required_args_exit_code_2() -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["audit", str(QUICKSTART)])
    assert excinfo.value.code == 2


def test_invalid_format_exit_code_2() -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["audit", str(QUICKSTART), "--sensitive", "sex", "--target", "target", "--format", "xml"])
    assert excinfo.value.code == 2


def test_unknown_subcommand_exit_code_2() -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["frobnicate", str(QUICKSTART)])
    assert excinfo.value.code == 2


def test_report_writes_artifacts(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    assert main(["report", str(QUICKSTART), "--sensitive", "group", "sex", "--target", "target", "-o", str(out_dir)]) == 0
    markdown = (out_dir / "report.md").read_text(encoding="utf-8")
    payload = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
    html = (out_dir / "report.html").read_text(encoding="utf-8")
    assert "Total issues: `2`" in markdown
    assert payload["summary"]["total_issues"] == 2
    assert "AuditLens bias audit report" in html
    assert "sensitive_correlation" in html
    assert len(list(out_dir.iterdir())) == 3


def test_python_dash_m_invocation() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "auditlens", "audit", str(QUICKSTART), "--sensitive", "sex", "--target", "target"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "Summary: 2 issue(s)" in result.stdout
