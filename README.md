# AuditLens

AuditLens is an agentic audit framework for machine learning datasets that combines deterministic statistics with LLM-based interpretation.

## Vision

Most bias tools stop at "a skew exists." AuditLens goes further: it explains whether that skew is harmful for a specific ML task, how severe the risk is, and what to do next.

The goal is to help teams catch data bias before model training and ship safer systems.

## The Core Idea

AuditLens takes two inputs:
- A dataset (CSV/tabular)
- A task description (for example: "predict loan default risk")

Then it runs a 3-layer pipeline:
- Layer 1: Deterministic statistical audit
- Layer 2: Task-aware LLM interpretation
- Layer 3: Structured report generation

## Architecture

### Layer 1: Statistical Audit (Deterministic)

Computes measurable dataset risk signals such as:
- Class imbalance
- Differential missingness by group
- Sensitive attribute correlation with target
- Subgroup label distribution and demographic parity gap

Output is strict JSON with metrics, issues, severity, and justification.

### Layer 2: Agent Interpretation (Task-Aware)

Consumes Layer 1 output plus task context and reasons about:
- Which issues are truly harmful for the stated ML objective
- Likely downstream model behavior and fairness risk
- Concrete mitigation options and implementation guidance

### Layer 3: Reporting

Generates a decision-ready report with:
- Executive summary
- Ranked risks
- Supporting visuals
- Mitigation recommendations
- Reproducibility details
- Human-review disclaimer

## Why This Matters

- Bias is contextual: not every skew is equally harmful for every task.
- Teams need ranked, actionable findings, not raw metrics alone.
- Deterministic-first design improves auditability and trust.

## Development Status

Implemented now:
- Week 1 foundation (Layer 1 backend and API)
- FastAPI endpoints: `/health`, `/upload`, `/analyze`
- Deterministic issue detection and severity scoring
- Automated tests with offline Adult Income smoke fixture

Planned next:
- Week 2: Agentic interpretation layer
- Week 3: Report generation + deployment
- Week 4: Evaluation suite and polish

## Quick Start

### 1) Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Run API

```bash
uvicorn backend.main:app --reload
```

Open:
- `http://127.0.0.1:8000/docs`

## API (Current)

- `GET /health`
- `POST /upload`
- `POST /analyze`

Example:

```bash
curl -X POST "http://127.0.0.1:8000/analyze" \
  -F "file=@sample.csv" \
  -F "target_column=income" \
  -F "sensitive_columns=sex,race"
```

## Testing

```bash
python -m pytest
```

Note:
- Adult Income smoke test is offline-safe via `tests/fixtures/adult.data`.

## Tech Stack

Current:
- Python, FastAPI, Pandas, SciPy, scikit-learn

Planned extension:
- LangGraph + LLM provider (OpenAI/Groq)
- Report generation (Markdown/PDF)
- Frontend and hosted deployment

## Repository Layout

```text
backend/
  layer1/
  routers/
  utils/
tests/
docs/
```

## References

- Project concept: `docs/main-idea.md`
- Full MVP plan: `docs/bias_audit_mvp_plan.md`

## License

No license file added yet.
