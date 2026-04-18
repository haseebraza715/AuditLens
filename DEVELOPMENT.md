# Development Guide

## Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
```

## Run API + Streamlit locally

Terminal 1 (FastAPI):

```bash
python3 -m uvicorn auditlens_server.app:app --reload --env-file .env
```

Terminal 2 (Streamlit):

```bash
python3 -m streamlit run ui/auditlens_ui/app.py
```

Or use `./run-dev.sh` after installing `.[ui]`.

## Commands

- Run all tests: `python3 -m pytest tests/`
- Quick syntax check on UI entrypoints:

```bash
python3 -m py_compile ui/auditlens_ui/app.py ui/auditlens_ui/state.py ui/auditlens_ui/api_client.py ui/auditlens_ui/workflow.py ui/auditlens_ui/ui.py ui/auditlens_ui/constants.py
```

- Single test file example: `python3 -m pytest tests/core/test_layer1.py`

## Conventions

- Keep severity thresholds in `src/auditlens/config.py` (`SEVERITY_THRESHOLDS`).
- Layer 1 lives under `src/auditlens/core/`; Layer 2 under `src/auditlens/interpretation/`; Layer 3 under `src/auditlens/reporting/`.
- Public notebook-style usage goes through `auditlens.audit` (`src/auditlens/api.py`).
