# AuditLens

## Overview

AuditLens is a bias-audit system for tabular ML datasets with a FastAPI backend and a Streamlit frontend.

Implemented layers:
- Layer 1: deterministic statistical bias checks
- Layer 2: task-aware interpretation and mitigation recommendations via LLM provider
- Layer 3: report generation (Markdown + PDF), artifacts, and async report jobs

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

Create a `.env` file for Layer 2 provider settings.

OpenRouter example:

```env
LAYER2_PROVIDER=openrouter
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=google/gemma-4-31b-it:free
```

Also supported:
- `LAYER2_PROVIDER=openai` with `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_BASE_URL`
- `LAYER2_PROVIDER=groq` with `GROQ_API_KEY`, `GROQ_MODEL`, `GROQ_BASE_URL`

## Run Locally

Terminal 1 (backend):

```bash
python3 -m uvicorn backend.main:app --reload --env-file .env
```

Terminal 2 (frontend):

```bash
python3 -m streamlit run frontend/app.py
```

Run tests:

```bash
python3 -m pytest
```

## Usage

### Streamlit UI

1. Upload a CSV file.
2. Select target and sensitive columns.
3. Enter task description.
4. Run audit.
5. If prompted, answer clarification questions.
6. Download PDF or Markdown report.

### API Endpoints

- `POST /upload`: validate CSV and return columns/shape preview
- `POST /analyze`: run Layer 1 only
- `POST /analyze-task`: run Layer 1 + Layer 2
- `POST /analyze-task-report`: return complete report + Markdown artifact
- `POST /analyze-task-report-pdf`: return complete report + PDF artifact (base64)
- `POST /analyze-task-report-store`: persist report artifact metadata
- `POST /analyze-task-report-jobs`: queue async report generation job
- `GET /analyze-task-report-jobs/{job_id}`: poll async job status/result
- `GET /reports/{artifact_id}`: artifact metadata
- `GET /reports/{artifact_id}/download`: artifact file download

### Python Layer 1 Entrypoint

```python
import pandas as pd
from backend.layer1.audit import run_layer1_audit

df = pd.read_csv("sample.csv")
report = run_layer1_audit(
    df=df,
    target_col="income",
    sensitive_cols=["sex", "race"],
)

print(report["summary"])
print(report["issues"])
```

## Limitations

- Layer 2 interpretation is LLM-assisted and may be inaccurate.
- Fairness recommendations require human review before deployment decisions.
- High-stakes use cases should include domain expert oversight.

See [ARCHITECTURE.md](./ARCHITECTURE.md) for system structure and flow.
