# Development Guide

## Run in Development Mode

```bash
python3 -m venv .venv
source .venv/bin/activate
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/uvicorn backend.main:app --reload
```

## Important Commands

- Run all tests:

```bash
.venv/bin/python -m pytest
```

- Run a single test file ([`tests/test_layer1.py`](./tests/test_layer1.py)):

```bash
.venv/bin/python -m pytest tests/test_layer1.py
```

- Run a single test case in [`tests/test_layer1.py`](./tests/test_layer1.py):

```bash
.venv/bin/python -m pytest tests/test_layer1.py::test_performance_100k_under_10_seconds
```

## Contributor Notes

- Keep Layer 1 deterministic. The same input should produce the same output.
- Add or update tests whenever analyzer behavior changes.
- Keep severity thresholds centralized in [`backend/utils/config.py`](./backend/utils/config.py).
- Preserve offline test reliability:
  - use local fixtures in [`tests/fixtures/`](./tests/fixtures/)
  - avoid introducing network dependencies in default test runs
- If you add new layers (agent/reporting), keep boundaries clear:
  - statistical computation in Layer 1
  - interpretation in Layer 2
  - presentation/reporting in Layer 3
