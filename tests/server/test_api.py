from __future__ import annotations

import io

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from auditlens_server.app import app

client = TestClient(app)


def _csv_bytes(content: str) -> bytes:
    return content.encode("utf-8")


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_preview() -> None:
    csv_text = "sex,race,target\nM,A,1\nF,B,0\n"
    response = client.post(
        "/upload",
        files={"file": ("sample.csv", _csv_bytes(csv_text), "text/csv")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["rows"] == 2
    assert payload["columns"] == 3


def test_analyze_valid_request() -> None:
    csv_text = "sex,race,target,feature\nM,A,1,10\nM,A,1,11\nF,B,0,12\nF,B,0,13\n"
    response = client.post(
        "/analyze",
        files={"file": ("sample.csv", _csv_bytes(csv_text), "text/csv")},
        data={
            "target_column": "target",
            "sensitive_columns": "sex,race",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["dataset_info"]["target_column"] == "target"
    assert payload["dataset_info"]["sensitive_columns"] == ["sex", "race"]


def test_analyze_missing_target_column() -> None:
    csv_text = "sex,race,label\nM,A,1\nF,B,0\n"
    response = client.post(
        "/analyze",
        files={"file": ("sample.csv", _csv_bytes(csv_text), "text/csv")},
        data={
            "target_column": "target",
            "sensitive_columns": "sex",
        },
    )
    assert response.status_code == 422
    assert "target_column" in response.json()["detail"]


def test_analyze_missing_sensitive_column() -> None:
    csv_text = "sex,race,target\nM,A,1\nF,B,0\n"
    response = client.post(
        "/analyze",
        files={"file": ("sample.csv", _csv_bytes(csv_text), "text/csv")},
        data={
            "target_column": "target",
            "sensitive_columns": "sex,ethnicity",
        },
    )
    assert response.status_code == 422
    assert "sensitive_columns" in response.json()["detail"]


def test_analyze_malformed_csv() -> None:
    malformed = b"not,a,csv\n1,2,3\n\x00\x00"
    response = client.post(
        "/analyze",
        files={"file": ("bad.csv", malformed, "text/csv")},
        data={
            "target_column": "target",
            "sensitive_columns": "sex",
        },
    )
    assert response.status_code == 422


def test_analyze_multiclass() -> None:
    csv_text = "sex,target,feature\nM,A,1\nM,A,2\nF,B,3\nF,C,4\nF,C,5\n"
    response = client.post(
        "/analyze",
        files={"file": ("sample.csv", _csv_bytes(csv_text), "text/csv")},
        data={
            "target_column": "target",
            "sensitive_columns": "sex",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert "issues" in payload


def test_analyze_repeated_sensitive_columns_form_list() -> None:
    csv_text = "sex,race,target\nM,A,1\nF,B,0\n"
    response = client.post(
        "/analyze",
        files=[
            ("file", ("sample.csv", _csv_bytes(csv_text), "text/csv")),
            ("target_column", (None, "target")),
            ("sensitive_columns", (None, "sex")),
            ("sensitive_columns", (None, "race")),
        ],
    )
    assert response.status_code == 200
    assert response.json()["dataset_info"]["sensitive_columns"] == ["sex", "race"]
