# AuditLens

Task-aware bias auditing for machine learning datasets.

AuditLens exists to help teams detect dataset bias early, prioritize real risk, and prepare actionable mitigation steps before model training.

## Key Features

- Deterministic statistical auditing of tabular datasets
- Severity-based issue ranking (`high`, `medium`, `low`)
- Multiple bias signals in one run:
  - class imbalance
  - differential missingness across groups
  - sensitive attribute correlation with target
  - subgroup label distribution and demographic parity gap
- Stable, schema-validated output for downstream processing
- Test coverage for correctness, determinism, and performance
- Offline-safe smoke test fixture for Adult Income dataset

## Product Direction

AuditLens is designed as a 3-layer system:

- Layer 1: Deterministic statistical audit (implemented)
- Layer 2: Task-aware LLM interpretation (planned)
- Layer 3: Report generation and delivery (planned)

Current repository status: Week 1 foundation is complete.

## Tech Stack

Current implementation:
- Python
- FastAPI
- Pandas
- NumPy
- SciPy
- scikit-learn
- Pydantic
- pytest

Planned additions:
- LangGraph + LLM provider
- Reporting tools (Markdown/PDF)
- Frontend and deployment layer

## Project Structure

```text
backend/
  main.py                # Application entrypoint
  routers/               # Request handling and input validation
  layer1/                # Statistical analyzers + audit orchestration
  utils/                 # Shared schemas and configuration
tests/
  fixtures/              # Local test datasets
  test_api.py            # API behavior tests
  test_layer1.py         # Core analyzer tests
  test_adult_income_smoke.py
docs/
  main-idea.md
  bias_audit_mvp_plan.md
```

## Setup and Installation

1. Clone the repository.
2. Create a virtual environment.
3. Install dependencies.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run the Project

Start the development server:

```bash
uvicorn backend.main:app --reload
```

The service will run locally and can be exercised from your preferred API client.

## Environment Variables

No environment variables are required for the current implementation.

Notes:
- There is currently no `.env` file or environment loader in use.
- When Layer 2 is added, API keys and model settings should be moved to environment variables.

## Usage Example

Use the core audit engine directly in Python:

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
```

Expected result:
- a dataset summary
- a list of ranked bias issues
- a severity count summary

## Demo / Screenshots

Placeholder:
- Add a short GIF or screenshot once UI/reporting layers are implemented.

## Quality Checks

Run tests:

```bash
python -m pytest
```

## License

No license file is currently included.
