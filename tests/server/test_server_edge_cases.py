"""Additional FastAPI endpoint coverage: validation, fallback, and error paths."""

from __future__ import annotations

import json
import time

import pytest

pytest.importorskip("fastapi")
from auditlens_server.app import app
from fastapi.testclient import TestClient

from auditlens.config import clear_layer2_settings_cache
from auditlens.interpretation.llm.base import BaseLLMClient

client = TestClient(app)


def _csv_bytes(content: str) -> bytes:
    return content.encode("utf-8")


def _post(path: str, csv_text: str, data: dict) -> object:
    return client.post(
        path,
        files=[("file", ("s.csv", _csv_bytes(csv_text), "text/csv"))]
        + [(k, (None, v)) for k, v in data.items()],
    )


class _GoodLLM(BaseLLMClient):
    def complete_json(self, prompt: str) -> str:
        if "Extract structured context" in prompt:
            return json.dumps(
                {
                    "task_type": "binary_classification",
                    "affected_population": "applicants",
                    "decision_impact": "approvals",
                    "stakes_level": "high",
                    "confidence": 0.95,
                }
            )
        if "Given task context and one statistical issue" in prompt:
            return json.dumps(
                {
                    "issue_id": "issue_1",
                    "why_harmful": "Subgroup skew.",
                    "at_risk_groups": [],
                    "likely_model_impact": "Uneven errors.",
                    "severity_delta": "equal",
                    "severity_rationale": "r",
                }
            )
        if "ML bias mitigation advisor" in prompt:
            return json.dumps({"mitigations": []})
        return "{}"


class _BrokenLLM(BaseLLMClient):
    def complete_json(self, prompt: str) -> str:
        return "not json"


class _ClarifyLLM(BaseLLMClient):
    def complete_json(self, prompt: str) -> str:
        if "Extract structured context" in prompt:
            return json.dumps(
                {
                    "task_type": "unknown",
                    "affected_population": "",
                    "decision_impact": "",
                    "confidence": 0.1,
                }
            )
        return "{}"


@pytest.fixture(autouse=True)
def _layer2_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LAYER2_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    clear_layer2_settings_cache()
    yield
    clear_layer2_settings_cache()


class TestAnalyzeValidation:
    def test_target_also_sensitive_rejected(self) -> None:
        csv = "target,g\n0,a\n1,b\n0,a\n1,b\n"
        response = _post("/analyze", csv, {"target_column": "target", "sensitive_columns": "target"})
        assert response.status_code == 422
        assert "must not also be" in response.json()["detail"]

    def test_empty_sensitive_columns_rejected(self) -> None:
        csv = "target,g\n0,a\n1,b\n"
        response = _post("/analyze", csv, {"target_column": "target", "sensitive_columns": "  "})
        assert response.status_code == 422

    def test_duplicate_sensitive_form_fields_deduped(self) -> None:
        csv = "sex,race,target\nM,A,1\nF,B,0\n"
        response = client.post(
            "/analyze",
            files=[
                ("file", ("s.csv", _csv_bytes(csv), "text/csv")),
                ("target_column", (None, "target")),
                ("sensitive_columns", (None, "sex")),
                ("sensitive_columns", (None, "sex,race")),
            ],
        )
        assert response.status_code == 200
        assert response.json()["dataset_info"]["sensitive_columns"] == ["sex", "race"]

    def test_single_row_csv_is_analyzed(self) -> None:
        csv = "sex,target\nM,1\n"
        response = _post("/analyze", csv, {"target_column": "target", "sensitive_columns": "sex"})
        assert response.status_code == 200
        assert response.json()["dataset_info"]["rows"] == 1

    def test_unicode_csv_columns(self) -> None:
        csv = "性别,目标\nF,1\nM,0\n"
        response = _post("/analyze", csv, {"target_column": "目标", "sensitive_columns": "性别"})
        assert response.status_code == 200


class TestAnalyzeTaskValidation:
    def test_task_description_too_long_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LAYER2_MAX_TASK_DESCRIPTION_CHARS", "200")
        clear_layer2_settings_cache()
        csv = "sex,target\nM,1\nF,0\n"
        response = _post(
            "/analyze-task",
            csv,
            {
                "target_column": "target",
                "sensitive_columns": "sex",
                "task_description": "word " * 60,
            },
        )
        assert response.status_code == 422
        assert "exceeds" in response.json()["detail"]

    def test_malformed_clarification_answers_rejected(self) -> None:
        csv = "sex,target\nM,1\nF,0\n"
        response = _post(
            "/analyze-task",
            csv,
            {
                "target_column": "target",
                "sensitive_columns": "sex",
                "task_description": "Predict outcomes",
                "clarification_answers": "{not json",
            },
        )
        assert response.status_code == 422
        assert "valid JSON" in response.json()["detail"]

    def test_scalar_clarification_answers_rejected(self) -> None:
        csv = "sex,target\nM,1\nF,0\n"
        response = _post(
            "/analyze-task",
            csv,
            {
                "target_column": "target",
                "sensitive_columns": "sex",
                "task_description": "Predict outcomes",
                "clarification_answers": "[1, 2]",
            },
        )
        assert response.status_code == 422

    def test_missing_api_key_returns_503(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        clear_layer2_settings_cache()
        csv = "sex,target\nM,1\nF,0\n"
        response = _post(
            "/analyze-task",
            csv,
            {
                "target_column": "target",
                "sensitive_columns": "sex",
                "task_description": "Predict outcomes",
            },
        )
        assert response.status_code == 503


class TestProviderFallback:
    def test_analyze_task_returns_502_without_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("auditlens.interpretation.pipeline.create_provider_client", lambda: _BrokenLLM())
        csv = "sex,target\nM,1\nF,0\n"
        response = _post(
            "/analyze-task",
            csv,
            {
                "target_column": "target",
                "sensitive_columns": "sex",
                "task_description": "Predict outcomes",
            },
        )
        assert response.status_code == 502

    def test_analyze_task_report_falls_back_to_layer1(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("auditlens.interpretation.pipeline.create_provider_client", lambda: _BrokenLLM())
        csv = "sex,target\nM,1\nF,0\n"
        response = _post(
            "/analyze-task-report",
            csv,
            {
                "target_column": "target",
                "sensitive_columns": "sex",
                "task_description": "Predict outcomes",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "complete"
        assert payload["report_artifact"]["format"] == "markdown"
        assert "Layer 2 interpretation unavailable" in payload["final_report"]["summary"]

    def test_store_endpoint_rejects_clarification_state(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("auditlens.interpretation.pipeline.create_provider_client", lambda: _ClarifyLLM())
        csv = "sex,target\nM,1\nF,0\n"
        response = _post(
            "/analyze-task-report-store",
            csv,
            {
                "target_column": "target",
                "sensitive_columns": "sex",
                "task_description": "Vague description",
            },
        )
        assert response.status_code == 422
        assert "clarification" in response.json()["detail"]

    def test_job_without_storage_has_no_stored_artifact(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        monkeypatch.setenv("AUDITLENS_ARTIFACT_DIR", str(tmp_path / "artifacts"))
        monkeypatch.setattr("auditlens.interpretation.pipeline.create_provider_client", lambda: _GoodLLM())
        clear_layer2_settings_cache()
        csv = "sex,target\nM,1\nF,0\n"
        create = _post(
            "/analyze-task-report-jobs",
            csv,
            {
                "target_column": "target",
                "sensitive_columns": "sex",
                "task_description": "Predict outcomes",
                "report_format": "markdown",
                "store_artifact": "false",
            },
        )
        assert create.status_code == 200
        job_id = create.json()["job_id"]
        final_payload = None
        for _ in range(30):
            status = client.get(f"/analyze-task-report-jobs/{job_id}")
            payload = status.json()
            if payload["status"] in {"complete", "failed"}:
                final_payload = payload
                break
            time.sleep(0.05)
        assert final_payload is not None
        assert final_payload["status"] == "complete"
        assert "report_artifact" in final_payload["result"]
        assert "stored_artifact" not in final_payload["result"]


class TestJobAndArtifactErrors:
    def test_unknown_job_returns_404(self) -> None:
        response = client.get("/analyze-task-report-jobs/not-a-real-job")
        assert response.status_code == 404

    def test_non_uuid_artifact_returns_404(self, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        monkeypatch.setenv("AUDITLENS_ARTIFACT_DIR", str(tmp_path / "a"))
        response = client.get("/reports/../../etc/passwd")
        assert response.status_code == 404

    def test_missing_artifact_content_returns_404(self, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AUDITLENS_ARTIFACT_DIR", str(tmp_path / "artifacts"))
        from auditlens.reporting.artifacts import save_report_artifact

        metadata = save_report_artifact(
            artifact_format="markdown", filename="r.md", content="# x", artifact_dir=tmp_path / "artifacts"
        )
        artifact_id = metadata["artifact_id"]
        (tmp_path / "artifacts" / f"{artifact_id}.md").unlink()
        assert client.get(f"/reports/{artifact_id}").status_code == 200
        assert client.get(f"/reports/{artifact_id}/download").status_code == 404

    def test_health_endpoint(self) -> None:
        assert client.get("/health").json() == {"status": "ok"}
