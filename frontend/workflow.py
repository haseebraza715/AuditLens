from __future__ import annotations

import base64
import io
import json
import time
from typing import Any

import pandas as pd
import streamlit as st

from backend.layer3.report_generator import build_markdown_report
from frontend.api_client import ApiError, get_json, post_form
from frontend.constants import ASYNC_ROW_THRESHOLD, POLL_INTERVAL_SECONDS
from frontend.state import reset_run_state


def upload_preview(file_name: str, file_bytes: bytes) -> dict[str, Any]:
    form = [("file", (file_name, file_bytes, "text/csv"))]
    return post_form("/upload", form, timeout=120)


def on_new_file(file_name: str, file_bytes: bytes) -> None:
    signature = f"{file_name}:{len(file_bytes)}"
    if signature == st.session_state.file_signature:
        return

    st.session_state.file_name = file_name
    st.session_state.file_bytes = file_bytes
    st.session_state.file_signature = signature
    st.session_state.preview_info = None
    st.session_state.df_preview = None
    st.session_state.target_column = None
    st.session_state.sensitive_columns = []
    reset_run_state()

    try:
        st.session_state.preview_info = upload_preview(file_name, file_bytes)
    except ApiError as exc:
        st.session_state.last_error = str(exc)
        return

    rows = int((st.session_state.preview_info or {}).get("rows", 0) or 0)
    st.session_state.use_async_mode = rows >= ASYNC_ROW_THRESHOLD

    try:
        df = pd.read_csv(io.BytesIO(file_bytes))
        st.session_state.df_preview = df.head(5)
    except Exception:
        st.session_state.df_preview = None

    column_names = list((st.session_state.preview_info or {}).get("column_names", []))
    if column_names:
        st.session_state.target_column = column_names[-1]


def build_analysis_form(
    *,
    file_name: str,
    file_bytes: bytes,
    target_column: str,
    sensitive_columns: list[str],
    task_description: str,
    clarification_answers: dict[str, Any] | None = None,
) -> list[tuple[str, tuple[Any, Any]]]:
    fields: list[tuple[str, tuple[Any, Any]]] = [
        ("file", (file_name, file_bytes, "text/csv")),
        ("target_column", (None, target_column)),
    ]
    for col in sensitive_columns:
        fields.append(("sensitive_columns", (None, col)))
    fields.append(("task_description", (None, task_description)))
    if clarification_answers:
        fields.append(("clarification_answers", (None, json.dumps(clarification_answers))))
    return fields


def fetch_layer1_report() -> None:
    if st.session_state.layer1_report is not None:
        return

    file_name = st.session_state.file_name
    file_bytes = st.session_state.file_bytes
    target = st.session_state.target_column
    sensitive = st.session_state.sensitive_columns
    if not file_name or not file_bytes or not target or not sensitive:
        return

    form: list[tuple[str, tuple[Any, Any]]] = [
        ("file", (file_name, file_bytes, "text/csv")),
        ("target_column", (None, target)),
    ]
    for col in sensitive:
        form.append(("sensitive_columns", (None, col)))

    try:
        st.session_state.layer1_report = post_form("/analyze", form, timeout=180)
    except ApiError as exc:
        st.warning(f"Layer 1 chart data unavailable: {exc}")


def fallback_to_markdown(form_fields: list[tuple[str, tuple[Any, Any]]]) -> dict[str, Any]:
    return post_form("/analyze-task-report", form_fields)


def submit_sync_audit(clarification_answers: dict[str, Any] | None = None) -> None:
    form = build_analysis_form(
        file_name=st.session_state.file_name,
        file_bytes=st.session_state.file_bytes,
        target_column=st.session_state.target_column,
        sensitive_columns=st.session_state.sensitive_columns,
        task_description=st.session_state.task_description,
        clarification_answers=clarification_answers,
    )

    try:
        response = post_form("/analyze-task-report-pdf", form)
    except ApiError as exc:
        if exc.status_code and exc.status_code >= 500:
            st.warning("PDF generation failed; retrying with Markdown endpoint.")
            response = fallback_to_markdown(form)
        else:
            raise

    consume_audit_response(response)


def submit_async_job(clarification_answers: dict[str, Any] | None = None) -> None:
    form = build_analysis_form(
        file_name=st.session_state.file_name,
        file_bytes=st.session_state.file_bytes,
        target_column=st.session_state.target_column,
        sensitive_columns=st.session_state.sensitive_columns,
        task_description=st.session_state.task_description,
        clarification_answers=clarification_answers,
    )
    form.append(("report_format", (None, "pdf_base64")))
    form.append(("store_artifact", (None, "true")))

    response = post_form("/analyze-task-report-jobs", form)
    st.session_state.pending_job_id = response.get("job_id")
    if st.session_state.pending_job_id:
        st.success(f"Async report job queued: {st.session_state.pending_job_id}")


def poll_async_job_if_needed() -> None:
    job_id = st.session_state.pending_job_id
    if not job_id:
        return

    st.info(f"Polling async job {job_id} every {POLL_INTERVAL_SECONDS} seconds...")
    try:
        job_status = get_json(f"/analyze-task-report-jobs/{job_id}", timeout=120)
    except ApiError as exc:
        st.error(f"Async polling failed: {exc}")
        st.session_state.pending_job_id = None
        return

    state = str(job_status.get("status", ""))
    if state in {"queued", "running"}:
        st.caption("Job is still running. Refreshing automatically...")
        time.sleep(POLL_INTERVAL_SECONDS)
        st.rerun()
        return

    if state == "failed":
        st.error(f"Async audit failed: {job_status.get('error', 'Unknown error')}")
        st.session_state.pending_job_id = None
        return

    if state != "complete":
        st.error(f"Unexpected job state: {state}")
        st.session_state.pending_job_id = None
        return

    result = job_status.get("result")
    if not isinstance(result, dict):
        st.error("Async audit returned invalid result payload.")
        st.session_state.pending_job_id = None
        return

    consume_audit_response(result)
    st.session_state.pending_job_id = None


def consume_audit_response(payload: dict[str, Any]) -> None:
    st.session_state.audit_response = payload
    st.session_state.last_error = None

    status = payload.get("status")
    if status == "needs_clarification":
        st.session_state.clarifying_questions = list(payload.get("clarifying_questions", []))
        st.session_state.task_context_partial = dict(payload.get("task_context_partial", {}))
        layer1 = payload.get("layer1_report")
        if isinstance(layer1, dict):
            st.session_state.layer1_report = layer1
        st.session_state.final_report = None
        st.session_state.report_artifact = None
        st.session_state.stored_artifact = None
        st.session_state.pdf_bytes = None
        st.session_state.markdown_text = None
        return

    if status != "complete":
        raise ApiError("Unexpected status from backend response.")

    final_report = payload.get("final_report")
    artifact = payload.get("report_artifact")
    stored_artifact = payload.get("stored_artifact")

    if not isinstance(final_report, dict):
        raise ApiError("Missing final_report in successful response.")

    st.session_state.final_report = final_report
    st.session_state.report_artifact = artifact if isinstance(artifact, dict) else None
    st.session_state.stored_artifact = stored_artifact if isinstance(stored_artifact, dict) else None
    st.session_state.clarifying_questions = []
    st.session_state.task_context_partial = {}

    if isinstance(artifact, dict):
        format_name = str(artifact.get("format", ""))
        content = str(artifact.get("content", ""))
        if format_name == "pdf_base64" and content:
            try:
                st.session_state.pdf_bytes = base64.b64decode(content)
            except Exception:
                st.warning("Could not decode PDF artifact from response.")
                st.session_state.pdf_bytes = None
        if format_name == "markdown" and content:
            st.session_state.markdown_text = content

    if st.session_state.markdown_text is None:
        try:
            st.session_state.markdown_text = build_markdown_report(
                final_report=final_report,
                layer1_report=st.session_state.layer1_report,
            )
        except Exception:
            st.session_state.markdown_text = ""


def clarification_payload_from_inputs() -> dict[str, Any]:
    questions = st.session_state.clarifying_questions
    answers = st.session_state.clarification_inputs
    payload: dict[str, Any] = {}
    freeform_assumptions: list[str] = []

    for question in questions:
        answer = str(answers.get(question, "")).strip()
        if not answer:
            continue

        q = question.lower()
        mapped = False
        if "task type" in q:
            lowered = answer.lower()
            if "binary" in lowered:
                payload["task_type"] = "binary_classification"
            elif "multiclass" in lowered or "multi-class" in lowered:
                payload["task_type"] = "multiclass_classification"
            elif "regression" in lowered:
                payload["task_type"] = "regression"
            else:
                payload["task_type"] = "unknown"
            mapped = True
        elif "who is affected" in q:
            payload["affected_population"] = answer
            mapped = True
        elif "what decisions" in q:
            payload["decision_impact"] = answer
            mapped = True
        elif "positive outcome" in q or "false positives" in q:
            payload["positive_class_meaning"] = answer
            payload["false_positive_consequence"] = answer
            payload["false_negative_consequence"] = answer
            mapped = True

        if not mapped:
            freeform_assumptions.append(answer)

    if freeform_assumptions:
        payload["assumptions"] = freeform_assumptions

    return payload


def start_audit_run() -> None:
    if not st.session_state.file_bytes:
        st.warning("Please upload a CSV before running the audit.")
        return
    if not st.session_state.target_column:
        st.warning("Please select a target column before running the audit.")
        return
    if not st.session_state.sensitive_columns:
        st.warning("Please select at least one sensitive column before running the audit.")
        return
    if not st.session_state.task_description.strip():
        st.warning("Please provide a task description before running the audit.")
        return

    preview = st.session_state.preview_info or {}
    rows = int(preview.get("rows", 0) or 0)
    use_async = bool(st.session_state.get("use_async_mode", rows >= ASYNC_ROW_THRESHOLD))

    try:
        with st.status("Running audit", expanded=True) as status_box:
            status_box.write(
                f"Dataset loaded ({rows} rows, {int(preview.get('columns', 0) or 0)} columns)"
            )
            fetch_layer1_report()
            status_box.write("Layer 1 - Statistical analysis complete")

            if use_async:
                status_box.write("Async mode selected - submitting report job...")
                submit_async_job()
                status_box.update(label="Async job submitted", state="running")
            else:
                status_box.write("Layer 2 - Interpreting findings for your task...")
                submit_sync_audit()
                status_box.write("Layer 3 - Report artifact generated")
                status_box.update(label="Audit complete", state="complete")
    except ApiError as exc:
        st.error(str(exc))


def submit_clarification_answers() -> None:
    clarification_payload = clarification_payload_from_inputs()
    if not clarification_payload:
        st.warning("Please answer at least one clarification question.")
        return

    preview = st.session_state.preview_info or {}
    rows = int(preview.get("rows", 0) or 0)
    use_async = bool(st.session_state.get("use_async_mode", rows >= ASYNC_ROW_THRESHOLD))

    try:
        with st.status("Submitting clarification answers", expanded=True) as status_box:
            status_box.write("Clarification answers collected")
            if use_async:
                status_box.write("Submitting async job with clarifications...")
                submit_async_job(clarification_answers=clarification_payload)
                status_box.update(label="Async clarification job submitted", state="running")
            else:
                status_box.write("Re-running Layer 2 and Layer 3...")
                submit_sync_audit(clarification_answers=clarification_payload)
                status_box.update(label="Clarified audit complete", state="complete")
    except ApiError as exc:
        st.error(str(exc))
