"""
Hardening tests: treat AuditLens like a product — edge cases, HTTP contract,
library UX, persistence, and packaging smoke.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _pythonpath_env() -> dict[str, str]:
    env = os.environ.copy()
    parts = [
        str(REPO_ROOT / "src"),
        str(REPO_ROOT / "server"),
        str(REPO_ROOT / "ui"),
    ]
    env["PYTHONPATH"] = os.pathsep.join(parts + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
    return env


# --- Public library API ---


def test_audit_empty_frame_returns_valid_report() -> None:
    from auditlens import audit

    df = pd.DataFrame({"t": pd.Series([], dtype=int), "s": pd.Series([], dtype=str)})
    report = audit(df, target_col="t", sensitive_cols=["s"])
    assert report.summary["total_issues"] == 0
    assert report.issues == []
    assert report.status is None
    md = report.to_markdown()
    assert "Layer 1" in md or "statistical" in md.lower()


def test_audit_single_row_binary() -> None:
    from auditlens import audit

    df = pd.DataFrame({"t": [1], "s": ["x"]})
    report = audit(df, target_col="t", sensitive_cols=["s"])
    assert isinstance(report.summary["total_issues"], int)
    blob = report.to_dict()
    assert blob["layer1_report"]["dataset_info"]["rows"] == 1


def test_audit_whitespace_only_task_description_skips_layer2() -> None:
    from auditlens import audit

    df = pd.DataFrame({"t": [0, 1, 0, 1], "s": ["a", "b", "a", "b"]})
    report = audit(df, target_col="t", sensitive_cols=["s"], task_description="   \n\t  ")
    assert report.status is None


def test_audit_custom_severity_thresholds_propagate() -> None:
    from auditlens import audit
    from auditlens.config import SEVERITY_THRESHOLDS

    df = pd.DataFrame({"y": [0] * 80 + [1] * 20, "g": ["A", "B"] * 50})
    loose = {k: dict(v) for k, v in SEVERITY_THRESHOLDS.items()}
    loose["imbalance_ratio"] = {"medium": 10.0, "high": 50.0}
    report_loose = audit(df, target_col="y", sensitive_cols=["g"], severity_thresholds=loose)
    report_default = audit(df, target_col="y", sensitive_cols=["g"])
    assert report_loose.summary["high_severity"] <= report_default.summary["high_severity"]


def test_audit_lens_report_to_pdf_requires_layer2() -> None:
    from auditlens import audit

    df = pd.DataFrame({"y": [0, 1, 0, 1], "g": ["a", "b", "a", "b"]})
    report = audit(df, target_col="y", sensitive_cols=["g"])
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        path = tmp.name
    try:
        with pytest.raises(ValueError, match="PDF export requires"):
            report.to_pdf(path)
    finally:
        Path(path).unlink(missing_ok=True)


def test_audit_lens_repr_html_with_no_issues() -> None:
    from auditlens import AuditLensReport

    empty_layer1 = {
        "dataset_info": {"rows": 0, "columns": 2, "target_column": "t", "sensitive_columns": ["s"]},
        "issues": [],
        "summary": {"total_issues": 0, "high_severity": 0, "medium_severity": 0, "low_severity": 0},
        "severity_thresholds": {},
    }
    r = AuditLensReport(empty_layer1, None)
    html = r._repr_html_()
    assert "No issues" in html or "0" in html


def test_audit_unicode_columns_and_values() -> None:
    from auditlens import audit

    df = pd.DataFrame({"目标": [0, 1, 0, 1], "组": ["α", "β", "α", "β"]})
    report = audit(df, target_col="目标", sensitive_cols=["组"])
    assert report.summary["total_issues"] >= 0
    assert "组" in repr(report.to_dict()["layer1_report"]["dataset_info"]["sensitive_columns"])


# --- Reporting ---


def test_build_markdown_includes_unicode_safely() -> None:
    from auditlens.reporting.generator import build_markdown_report

    final_report = {
        "task_description": "Prédictions — test",
        "task_context": {"task_type": "binary_classification", "stakes_level": "high"},
        "issues": [
            {
                "statistical_issue": {
                    "issue_id": "i1",
                    "type": "class_imbalance",
                    "severity": "high",
                    "description": "Text with émojis 🔍 and <tags>",
                },
                "interpretation": {
                    "why_harmful": "Résumé",
                    "severity_delta": "equal",
                    "severity_rationale": "—",
                    "likely_model_impact": "n/a",
                },
                "mitigations": [],
            }
        ],
        "summary": "S",
        "disclaimer": "D",
        "reproducibility": {},
    }
    md = build_markdown_report(final_report=final_report, layer1_report=None)
    assert "Prédictions" in md
    assert "Résumé" in md


# --- Artifacts ---


def test_artifact_save_and_metadata_roundtrip() -> None:
    from auditlens.reporting.artifacts import get_artifact_metadata, save_report_artifact

    with tempfile.TemporaryDirectory() as tmp:
        meta = save_report_artifact(
            artifact_format="markdown",
            filename="r.md",
            content="# hello\n",
            artifact_dir=tmp,
        )
        aid = meta["artifact_id"]
        loaded = get_artifact_metadata(aid, artifact_dir=tmp)
        assert loaded["artifact_id"] == aid
        assert loaded["format"] == "markdown"


def test_artifact_pdf_roundtrip_from_base64() -> None:
    from auditlens.reporting.artifacts import get_artifact_metadata, save_report_artifact

    pdf_bytes = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
    b64 = base64.b64encode(pdf_bytes).decode("ascii")
    with tempfile.TemporaryDirectory() as tmp:
        meta = save_report_artifact(
            artifact_format="pdf_base64",
            filename="x.pdf",
            content=b64,
            artifact_dir=tmp,
        )
        loaded = get_artifact_metadata(meta["artifact_id"], artifact_dir=tmp)
        assert loaded["format"] == "pdf_base64"


# --- Fresh interpreter: no eager LangGraph ---


def test_import_audit_does_not_load_langgraph_until_layer2() -> None:
    code = """
import sys
from auditlens import audit
import pandas as pd
assert "langgraph" not in sys.modules
df = pd.DataFrame({"t": [0, 1, 0, 1], "s": ["a", "b", "a", "b"]})
r = audit(df, target_col="t", sensitive_cols=["s"])
assert "langgraph" not in sys.modules
_ = r.to_markdown()
assert "langgraph" not in sys.modules
"""
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(REPO_ROOT),
        env=_pythonpath_env(),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


# --- Packaging ---


@pytest.mark.slow
def test_project_builds_wheel_and_sdist() -> None:
    dist_dir = REPO_ROOT / "dist"
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "build"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert proc.returncode == 0, proc.stderr
        if dist_dir.exists():
            import shutil

            shutil.rmtree(dist_dir)
        proc = subprocess.run(
            [sys.executable, "-m", "build", "--outdir", str(dist_dir)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        wheels = list(dist_dir.glob("*.whl"))
        sdists = list(dist_dir.glob("*.tar.gz"))
        assert wheels, "expected at least one wheel"
        assert sdists, "expected sdist"
        whl = wheels[0]
        assert "auditlens" in whl.name.lower()
    finally:
        if dist_dir.exists():
            import shutil

            shutil.rmtree(dist_dir, ignore_errors=True)


@pytest.mark.slow
def test_twine_check_passes_on_built_artifacts() -> None:
    dist_dir = REPO_ROOT / "dist"
    import shutil

    proc = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "build", "twine"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    proc = subprocess.run(
        [sys.executable, "-m", "build", "--outdir", str(dist_dir)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    try:
        artifacts = sorted(dist_dir.glob("auditlens-*"))
        assert artifacts, "expected built artifacts in dist/"
        proc = subprocess.run(
            [sys.executable, "-m", "twine", "check", *[str(p) for p in artifacts]],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
    finally:
        shutil.rmtree(dist_dir, ignore_errors=True)


# --- HTTP API (FastAPI) ---


def test_server_health_contract() -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from auditlens_server.app import app

    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_server_analyze_rejects_empty_upload() -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from auditlens_server.app import app

    client = TestClient(app)
    r = client.post(
        "/analyze",
        files={"file": ("empty.csv", b"", "text/csv")},
        data={"target_column": "t", "sensitive_columns": "s"},
    )
    assert r.status_code == 422


def test_server_upload_rejects_empty_file() -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from auditlens_server.app import app

    client = TestClient(app)
    r = client.post("/upload", files={"file": ("empty.csv", b"", "text/csv")})
    assert r.status_code == 422


def test_server_analyze_task_requires_nonempty_task_description() -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from auditlens_server.app import app

    client = TestClient(app)
    csv_text = "sex,target\nM,1\nF,0\n"
    r = client.post(
        "/analyze-task",
        files={"file": ("s.csv", csv_text.encode(), "text/csv")},
        data={
            "target_column": "target",
            "sensitive_columns": "sex",
            "task_description": "   ",
        },
    )
    assert r.status_code == 422


# --- Layer 2 pipeline with injected client (no network) ---


def test_run_layer2_pipeline_complete_with_scripted_llm() -> None:
    from auditlens.interpretation.llm.base import BaseLLMClient
    from auditlens.interpretation.pipeline import run_layer2_pipeline

    class _MiniLLM(BaseLLMClient):
        def complete_json(self, prompt: str) -> str:
            if "Extract structured context" in prompt:
                return json.dumps(
                    {
                        "task_type": "binary_classification",
                        "affected_population": "users",
                        "decision_impact": "x",
                        "stakes_level": "high",
                        "confidence": 0.9,
                        "needs_clarification": False,
                    }
                )
            if "Given task context and one statistical issue" in prompt:
                import re

                m = re.search(r'"issue_id"\s*:\s*"([^"]+)"', prompt)
                iid = m.group(1) if m else "ix"
                return json.dumps(
                    {
                        "issue_id": iid,
                        "why_harmful": "harm",
                        "at_risk_groups": [],
                        "likely_model_impact": "impact",
                        "severity_delta": "equal",
                        "severity_rationale": "r",
                    }
                )
            if "ML bias mitigation advisor" in prompt:
                return json.dumps(
                    {
                        "mitigations": [
                            {
                                "title": "t",
                                "category": "c",
                                "when_to_use": "w",
                                "tradeoffs": "tr",
                                "difficulty": "easy",
                                "expected_impact": "e",
                                "code_snippet": "pass",
                            }
                        ]
                    }
                )
            return "{}"

    layer1 = {
        "dataset_info": {"rows": 4, "columns": 2, "target_column": "t", "sensitive_columns": ["s"]},
        "issues": [
            {
                "issue_id": "one_issue",
                "type": "class_imbalance",
                "description": "imbalance",
                "affected_column": "t",
                "severity": "high",
                "metrics": {"imbalance_ratio": 4.0},
                "justification": "j",
            }
        ],
        "summary": {"total_issues": 1, "high_severity": 1, "medium_severity": 0, "low_severity": 0},
        "severity_thresholds": {},
    }
    out = run_layer2_pipeline(
        layer1_report=layer1,
        task_description="binary classification task",
        llm_client=_MiniLLM(),
        layer2_provider="test",
        layer2_model="test",
    )
    assert out["status"] == "complete"
    assert "final_report" in out
    assert out["final_report"]["issues"]


# --- Regression: pydantic layer1 response shape ---


def test_layer1_payload_strips_internal_thresholds_for_http_shape() -> None:
    from auditlens.core.audit import run_layer1_audit
    from auditlens.core.schema import AuditReport

    df = pd.DataFrame({"y": [0, 1, 0, 1], "g": ["a", "b", "a", "b"]})
    raw = run_layer1_audit(df, "y", ["g"])
    assert "severity_thresholds" in raw
    public = {k: v for k, v in raw.items() if k != "severity_thresholds"}
    model = AuditReport.model_validate(public)
    assert model.summary.total_issues >= 0


# --- Smoke: adult fixture still loads (dataset integrity) ---


def test_adult_fixture_readable() -> None:
    path = REPO_ROOT / "tests" / "fixtures" / "adult.data"
    assert path.is_file()
    df = pd.read_csv(path, header=None, nrows=5)
    assert df.shape[0] == 5
