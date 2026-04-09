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
python -m pytest
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

For system design details, see `ARCHITECTURE.md`.
