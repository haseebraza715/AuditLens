# AuditLens

## Overview

AuditLens is a FastAPI service for deterministic bias auditing on tabular datasets before model training.

Current implementation includes Layer 1 (statistical audit):
- class distribution checks
- missingness analysis by sensitive group
- sensitive attribute correlation checks
- subgroup outcome parity checks
- severity scoring and ranked issue output

Planned layers:
- Layer 2: task-aware interpretation
- Layer 3: report generation and delivery

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the API locally:

```bash
uvicorn backend.main:app --reload
```

Run tests:

```bash
python3 -m pytest
```

## Usage

Use the Python audit entrypoint directly:

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

Use the API:
- start the server with `uvicorn backend.main:app --reload`
- open `http://127.0.0.1:8000/docs`
- call the audit endpoint with dataset, target column, and sensitive columns

Layer 2 task-aware endpoint:
- use `POST /analyze-task` with the same CSV inputs plus required `task_description`
- optional `clarification_answers` JSON can be sent on follow-up requests
- response status is either `needs_clarification` or `complete`

Layer 3 report endpoint:
- use `POST /analyze-task-report` with the same inputs as `/analyze-task`
- on completion, response includes `report_artifact` with Markdown report content (`auditlens_report.md`)
- if task context is ambiguous, response returns `needs_clarification` before report generation
- use `POST /analyze-task-report-pdf` to receive PDF output as base64 in `report_artifact.content` (`auditlens_report.pdf`)

Example clarification follow-up:
- first call returns `needs_clarification` with targeted questions
- second call includes JSON answers in `clarification_answers` to receive `complete`

## Limitations

- Layer 2 interpretation is LLM-assisted and can be wrong.
- Recommendations should be reviewed by a qualified practitioner before deployment decisions.
- Human review is strongly recommended for high-stakes use cases.

For system design details, see [ARCHITECTURE.md](./ARCHITECTURE.md).
