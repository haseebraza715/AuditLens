# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
