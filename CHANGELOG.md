# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- CLI: `auditlens` console script and `python -m auditlens` with `audit` (findings table or JSON) and `report` (markdown/HTML/JSON artifacts) subcommands; thin wrapper over the library pipeline, covered by `tests/test_cli.py`.
- Pytest markers `slow` and `e2e`; CI matrix runs the fast suite while a dedicated job runs packaging (`slow`) and Playwright API checks against uvicorn (`e2e`).
- Optional extra `[e2e]` (Playwright) and `tests/e2e/` for live-server HTTP verification; e2e paths are ignored when Playwright is not installed.
- `httpx2` in the `[dev]` extra (Starlette >= 1.0 TestClient prefers it over the deprecated `httpx` path).
- Early validation of custom severity-threshold tables with clear `AuditLensError` messages.

### Fixed

- Correlation analyzer no longer crashes when a numeric column contains `inf` (previously `pd.qcut` raised); constant columns are skipped instead of emitting scipy warnings; Cramer's V is clamped to `[0, 1]` and non-finite chi-square tables report 1.0.
- Severity scoring rejects non-finite metrics instead of silently labeling them "low".
- `audit()` rejects `target_col` also listed in `sensitive_cols`, deduplicates repeated sensitive columns, and validates the DataFrame type with clear errors.
- `AuditLensReport.to_dict()` is now strict-JSON-safe: `inf`/`NaN` metrics are emitted as `null`.
- Artifact saving validates base64 content before writing (clear `ValueError` instead of a partial file).
- PDF export is byte-reproducible for identical inputs (`invariant=True`).
- `start_report_job` accepts an injectable job store for testability.
- Server router: deduplicated the duplicated Layer 2 form/raw-bytes execution path and added `target == sensitive` validation on all endpoints.

## [0.1.0] - 2026-04-18

### Added

- Pip-installable `auditlens` package (`src/` layout) with core statistical audits (Layer 1).
- Public API: `audit()` and `AuditLensReport` (summary, issues, `to_markdown()`, `to_pdf()`, Jupyter HTML repr).
- Optional extras: `[openai]`, `[groq]`, `[openrouter]`, `[pdf]`, `[viz]`, `[server]`, `[ui]`, `[all]`, `[dev]`.
- `auditlens_server` (FastAPI) and `auditlens_ui` (Streamlit) as optional install surfaces.
- Examples: `examples/notebook_quickstart.ipynb`, `examples/custom_llm_client.py`.

### Changed

- Repository layout: library under `src/auditlens/`, internal planning docs under `docs/internal/`.

### Removed

- Legacy empty `backend/` package stubs (code now lives under `src/auditlens/`).
