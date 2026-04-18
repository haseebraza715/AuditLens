"""End-to-end HTTP checks via Playwright's request API (no browser UI)."""

from __future__ import annotations

import pytest
from playwright.sync_api import APIRequestContext

pytestmark = pytest.mark.e2e


def test_health_via_playwright(playwright_request: APIRequestContext) -> None:
    r = playwright_request.get("/health")
    assert r.ok, r.text
    assert r.json() == {"status": "ok"}


def test_upload_preview_via_playwright(playwright_request: APIRequestContext) -> None:
    csv_bytes = b"sex,race,target\nM,A,1\nF,B,0\n"
    r = playwright_request.post(
        "/upload",
        multipart={
            "file": {"name": "sample.csv", "mimeType": "text/csv", "buffer": csv_bytes},
        },
    )
    assert r.ok, r.text
    body = r.json()
    assert body["rows"] == 2
    assert body["columns"] == 3


def test_analyze_layer1_via_playwright(playwright_request: APIRequestContext) -> None:
    csv_bytes = b"sex,race,target,feature\nM,A,1,10\nM,A,1,11\nF,B,0,12\nF,B,0,13\n"
    r = playwright_request.post(
        "/analyze",
        multipart={
            "file": {"name": "sample.csv", "mimeType": "text/csv", "buffer": csv_bytes},
            "target_column": "target",
            "sensitive_columns": "sex,race",
        },
    )
    assert r.ok, r.text
    body = r.json()
    assert body["dataset_info"]["target_column"] == "target"
    assert body["dataset_info"]["sensitive_columns"] == ["sex", "race"]


def test_analyze_validation_error_via_playwright(playwright_request: APIRequestContext) -> None:
    csv_bytes = b"sex,race,label\nM,A,1\nF,B,0\n"
    r = playwright_request.post(
        "/analyze",
        multipart={
            "file": {"name": "sample.csv", "mimeType": "text/csv", "buffer": csv_bytes},
            "target_column": "target",
            "sensitive_columns": "sex",
        },
    )
    assert r.status == 422
    detail = r.json().get("detail", "")
    flat = detail if isinstance(detail, str) else repr(detail)
    assert "target_column" in flat.lower()
