# AuditLens

AuditLens is a bias-audit backend for tabular ML datasets.

It analyzes a CSV dataset with respect to a target column and sensitive attributes, then returns a structured JSON report with detected issues and severity levels.

## Current Status

Week 1 (Statistical Layer) is complete.

Implemented:
- FastAPI backend with upload + analyze endpoints
- Deterministic Layer 1 bias checks
- Severity scoring and issue ranking
- Test suite with offline Adult Income smoke fixture

Planned next (not implemented yet):
- Week 2: Task-aware LLM/agent interpretation layer
- Week 3: Report generation + deployment
- Week 4: Evaluation suite and full documentation polish

## What AuditLens Detects (Layer 1)

- Class imbalance in target label
- Differential missingness across sensitive groups
- Sensitive attribute correlation with target
- Demographic parity gap by subgroup

Every issue includes:
- `issue_id`
- `type`
- `description`
- `severity` (`high` / `medium` / `low`)
- metric details
- threshold-based justification

## API Endpoints

- `GET /health`
- `POST /upload`
- `POST /analyze`

### `POST /upload`

Accepts a CSV file and returns:
- row count
- column count
- list of columns

### `POST /analyze`

Inputs:
- `file` (CSV)
- `target_column` (form field)
- `sensitive_columns` (form field, comma-separated or repeated entries)

Output:
- `dataset_info`
- `issues` (sorted by severity, then id)
- `summary` counts by severity

## Quick Start

### 1. Create and activate virtualenv

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run API

```bash
uvicorn backend.main:app --reload
```

Server starts at:
- `http://127.0.0.1:8000`
- Docs: `http://127.0.0.1:8000/docs`

## Example Usage

### Health check

```bash
curl http://127.0.0.1:8000/health
```

### Upload preview

```bash
curl -X POST "http://127.0.0.1:8000/upload" \
  -F "file=@sample.csv"
```

### Analyze

```bash
curl -X POST "http://127.0.0.1:8000/analyze" \
  -F "file=@sample.csv" \
  -F "target_column=income" \
  -F "sensitive_columns=sex,race"
```

## Run Tests

```bash
python -m pytest
```

Notes:
- The Adult Income smoke test uses a local fixture at `tests/fixtures/adult.data` (offline-safe).
- Current suite should pass fully (`16 passed`).

## Project Structure

```text
backend/
  main.py
  routers/audit.py
  layer1/
    audit.py
    class_distribution.py
    missing_values.py
    correlations.py
    subgroup_analysis.py
    severity_scorer.py
  utils/
    schema.py
    config.py
tests/
  test_api.py
  test_layer1.py
  test_adult_income_smoke.py
  fixtures/adult.data
docs/
  main-idea.md
  bias_audit_mvp_plan.md
```

## Limitations (Current MVP)

- Layer 2 task-aware interpretation is not integrated yet.
- No frontend UI yet.
- No PDF/report generation yet.

## License

No license file has been added yet.
