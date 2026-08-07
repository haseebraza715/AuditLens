# AuditLens

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)
[![CI](https://github.com/haseebraza715/AuditLens/actions/workflows/ci.yml/badge.svg)](https://github.com/haseebraza715/AuditLens/actions/workflows/ci.yml)

**Audit a dataset's statistics before you trust an LLM's opinion — deterministic checks + shareable reports.**

![AuditLens demo](docs/demo.gif)

## Try it in 60 seconds

```bash
git clone https://github.com/haseebraza715/AuditLens.git && cd AuditLens
python3 -m venv .venv && source .venv/bin/activate
python3 -m pip install -e .
./scripts/demo.sh
```

**What you'll see:**

- A **severity summary bar** — 2 HIGH, 0 MEDIUM, 0 LOW across the four bundled checks.
- **Two HIGH findings, pinned to exact locations and metrics** — `|r| = 0.500` (point-biserial, n=8) for `sex ↔ target` correlation, and a demographic-parity gap of `Δ = 0.500` (positive rate F=0.25 vs M=0.75, n=8) — each with its own justification.
- **A shareable markdown report and a 4-page PDF** written to `demo-output/` — generated with zero network, zero API keys, and no LLM.

## What it does

- **Layer 1 — deterministic statistical checks (always on):** class imbalance, differential missingness by group, sensitive-column ↔ target correlation, and subgroup demographic-parity gaps. The same CSV in produces the same findings out — no randomness, no network, no model.
- **Layer 2 — optional LLM interpretation:** enable it per-call (`task_description=...`) and a provider (OpenAI, OpenRouter, Groq, or any `BaseLLMClient`) explains the statistical evidence *on top of* — never instead of — Layer 1.
- **Shareable reports:** byte-reproducible markdown, HTML tables for Jupyter, and PDFs with charts — every finding carries severity, location, metric value, and justification.
- **Jupyter-friendly:** a report on the last line of a cell renders as an HTML table (`_repr_html_`); `report.to_dict()` gives a JSON snapshot for pipelines.
- **Optional server and UI extras:** `pip install -e ".[server]"` for a FastAPI HTTP API, `".[ui]"` for a Streamlit front end.
- **PyPI-ready:** CI runs the test matrix on 3.9/3.11/3.12, and a Trusted-Publishing workflow releases to PyPI (`pip install auditlens` once the first release is cut).

## How it works

Statistics first, interpretation second. `audit()` runs Layer 1 checks against fixed magnitude thresholds, tags each finding with a severity and an exact location (column, metric, sample size), and composes the report. Layer 2, when enabled, reads only that evidence — so the LLM can't invent findings. Reports carry provenance (`generated_at`, provider/model, thresholds), so any audit can be reproduced on demand.

## Quick facts

| | |
| --- | --- |
| Language | Python ≥ 3.9 |
| Dependencies | pandas, numpy, scipy, scikit-learn, pydantic (core); extras for LLM, PDF, server, UI |
| Offline? | Yes — Layer 1 needs no network, accounts, or API keys |
| Interfaces | Library (`audit()`), optional FastAPI server, optional Streamlit UI |
| License | MIT |

## Quickstart (library)

```python
from auditlens import audit
import pandas as pd

df = pd.read_csv("examples/quickstart.csv")  # committed synthetic example
report = audit(
    df,
    target_col="target",
    sensitive_cols=["group", "sex"],
)
print(report.summary)       # severity counts (dict)
print(len(report.issues))   # structured AuditIssue list
print(report.to_markdown()[:500])
```

The example CSV is synthetic (CC0-1.0) and committed with the repo, so the
snippet is deterministic and needs no downloads or network. Its versioned
output and provenance live in
[`docs/examples/quickstart-result.md`](docs/examples/quickstart-result.md) and
are re-verified by CI.

> **Severity is effect-size based, not significance-based.** Layer 1 flags
> issues purely from gap/correlation magnitudes against fixed thresholds
> (`SEVERITY_THRESHOLDS`) and runs no hypothesis tests. With small samples
> (e.g. the bundled 8-row example) a large-looking gap or correlation carries
> wide sampling error; treat findings as screening signals and validate on
> larger data before acting on them.

- **Layer 1 only (default install):** omit `task_description`. You still get `summary`, `issues`, and `to_markdown()` — plus PDF export via `report.to_pdf("report.pdf")`.
- **Layer 2:** pass a non-empty `task_description` and install an LLM extra (e.g. `pip install -e ".[openai]"`), configure provider env vars, or pass a `BaseLLMClient` instance (see `examples/custom_llm_client.py`).
- **PDF:** `pip install -e ".[pdf]"` (ReportLab + matplotlib) enables `to_pdf()` for Layer 1-only and completed Layer 2 reports.

## Install extras

| Extra | Purpose |
| --- | --- |
| *(core only)* | Layer 1, schemas, `audit()` without LLM |
| `openai` | LangGraph + LangChain + OpenAI SDK for Layer 2 |
| `groq` / `openrouter` | Same stack as `openai` (OpenAI-compatible clients) |
| `pdf` | ReportLab + matplotlib for `to_pdf()` |
| `viz` | matplotlib only (charts) |
| `server` | FastAPI + Uvicorn HTTP API |
| `ui` | Streamlit app (pulls in `server`) |
| `all` | All of the above |
| `dev` | pytest, httpx, ruff, and extras for the test suite |
| `e2e` | Playwright for HTTP e2e tests in `tests/e2e/` |

## Layer 2 providers

Install `openai` (or `server`/`ui`) and set environment variables, for example:

**OpenRouter**

```env
LAYER2_PROVIDER=openrouter
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=google/gemma-4-31b-it:free
```

**OpenAI**

```env
LAYER2_PROVIDER=openai
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1
```

**Groq**

```env
LAYER2_PROVIDER=groq
GROQ_API_KEY=your_key
GROQ_MODEL=llama-3.1-70b-versatile
GROQ_BASE_URL=https://api.groq.com/openai/v1
```

Optional tuning: `LAYER2_TIMEOUT_SECONDS`, `LAYER2_MAX_RETRIES`, `LAYER2_MAX_TASK_DESCRIPTION_CHARS`.

## Optional server and UI

```bash
python3 -m pip install -e ".[server]"
python3 -m uvicorn auditlens_server.app:app --reload --env-file .env
```

Endpoints include `POST /upload`, `POST /analyze`, `POST /analyze-task`, report routes, and async jobs. The server is intentionally single-process: async report jobs live in memory, are lost on restart, and don't span Uvicorn workers. Uploads default to a 10 MiB / 100,000-row limit — configure `AUDITLENS_MAX_UPLOAD_BYTES` / `AUDITLENS_MAX_UPLOAD_ROWS` before startup.

```bash
python3 -m pip install -e ".[ui]"
python3 -m streamlit run ui/auditlens_ui/app.py
```

Or run `./run-dev.sh` after installing `.[ui]` into `.venv`.

## Development

```bash
python3 -m pip install -e ".[dev]"
python3 -m pytest tests/ -m "not slow and not e2e"   # fast suite, matches CI
python3 -m ruff check src tests scripts
```

Full suite (packaging smoke + live-server Playwright):

```bash
python3 -m pip install -e ".[dev,e2e]"
python3 -m playwright install chromium
python3 -m pytest tests/
```

## Layout

- `src/auditlens/` — installable package (`core`, `interpretation`, `reporting`, public `audit()` API)
- `server/auditlens_server/` — FastAPI app (optional extra)
- `ui/auditlens_ui/` — Streamlit UI (optional extra)
- `scripts/demo.sh` — offline one-command demo
- `tests/` — unit, integration, and smoke tests by area

`pip install auditlens` ships only the packages under `src/`, `server/`, and `ui/`; tests, notebooks, and docs stay in the repo.

## Publishing (maintainers)

GitHub Actions under `.github/workflows/`: `ci.yml` runs the fast matrix on Python 3.9/3.11/3.12 plus separate slow-packaging and Playwright e2e jobs; `publish-pypi.yml` builds and publishes via **Trusted Publishing** (OIDC, no tokens). To publish, keep `version` in `pyproject.toml` in sync with the release tag (e.g. `v0.1.0`), then create a GitHub Release — or run the workflow manually. Manual fallback: `python -m build && twine upload dist/*` with a token.
