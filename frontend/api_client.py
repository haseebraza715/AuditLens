from __future__ import annotations

import json
from typing import Any

import requests
import streamlit as st

from frontend.constants import REQUEST_TIMEOUT_SECONDS


class ApiError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _api_url(path: str) -> str:
    return f"{st.session_state.api_base_url.rstrip('/')}{path}"


def _extract_error_detail(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text.strip() or f"HTTP {response.status_code}"

    detail = payload.get("detail", "") if isinstance(payload, dict) else ""
    if isinstance(detail, list):
        return "; ".join(str(item) for item in detail)
    if isinstance(detail, dict):
        return json.dumps(detail)
    if detail:
        return str(detail)
    return f"HTTP {response.status_code}"


def _friendly_error_message(status_code: int, detail: str) -> str:
    lower = detail.lower()
    if status_code == 422 and ("malformed csv" in lower or "uploaded csv is empty" in lower):
        return "Could not read this file. Make sure it is a valid CSV."
    if status_code == 503:
        return "Interpretation service unavailable. Check your API key in settings."
    if status_code == 502:
        if "provider" in lower or "model" in lower or "layer 2" in lower:
            return "Interpretation provider request failed. Check Layer 2 API credentials/model config."
        return "Backend failed while generating task interpretation. Try again or use Layer 1-only analysis."
    if status_code in (408, 504):
        return "The audit is taking longer than expected. Try a smaller dataset or use async mode."
    return detail or f"Request failed with status {status_code}."


def post_form(
    path: str,
    fields: list[tuple[str, tuple[Any, Any]]],
    timeout: int = REQUEST_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    try:
        response = requests.post(_api_url(path), files=fields, timeout=timeout)
    except requests.Timeout as exc:
        raise ApiError(
            "The audit is taking longer than expected. Try a smaller dataset or use async mode."
        ) from exc
    except requests.RequestException as exc:
        raise ApiError(f"Could not reach backend API: {exc}") from exc

    if not response.ok:
        detail = _extract_error_detail(response)
        raise ApiError(
            _friendly_error_message(response.status_code, detail),
            status_code=response.status_code,
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise ApiError("Backend returned invalid JSON response.") from exc
    if not isinstance(payload, dict):
        raise ApiError("Backend returned an unexpected response shape.")
    return payload


def get_json(path: str, timeout: int = REQUEST_TIMEOUT_SECONDS) -> dict[str, Any]:
    try:
        response = requests.get(_api_url(path), timeout=timeout)
    except requests.Timeout as exc:
        raise ApiError("Request timed out while polling report job.") from exc
    except requests.RequestException as exc:
        raise ApiError(f"Could not reach backend API: {exc}") from exc

    if not response.ok:
        detail = _extract_error_detail(response)
        raise ApiError(
            _friendly_error_message(response.status_code, detail),
            status_code=response.status_code,
        )

    data = response.json()
    if not isinstance(data, dict):
        raise ApiError("Backend returned an unexpected response shape.")
    return data


def download_bytes(path: str, timeout: int = REQUEST_TIMEOUT_SECONDS) -> bytes:
    try:
        response = requests.get(_api_url(path), timeout=timeout)
    except requests.RequestException as exc:
        raise ApiError(f"Failed to download artifact: {exc}") from exc

    if not response.ok:
        detail = _extract_error_detail(response)
        raise ApiError(
            _friendly_error_message(response.status_code, detail),
            status_code=response.status_code,
        )
    return response.content
