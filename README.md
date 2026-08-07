# AuditLens

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)
[![CI](https://github.com/haseebraza715/AuditLens/actions/workflows/ci.yml/badge.svg)](https://github.com/haseebraza715/AuditLens/actions/workflows/ci.yml)

**A statistical audit of your dataset before you trust an LLM's read of it, with shareable reports.**

![AuditLens demo](docs/demo.gif)

## Try it in 60 seconds

```bash
git clone https://github.com/haseebraza715/AuditLens.git && cd AuditLens
python3 -m venv .venv && source .venv/bin/activate
python3 -m pip install -e .
./scripts/demo.sh
```

**What you'll see:**

- A severity summary bar: 2 HIGH, 0 MEDIUM, 0 LOW.
- **Two HIGH findings pinned to exact metrics**: `|r| = 0.500` (point-biserial, n=8) for `sex ↔ target`, and a demographic-parity gap of `Δ = 0.500` (F=0.25 vs M=0.75, n=8).
- A shareable markdown report and a PDF in `demo-output/`: zero network, zero API keys, no LLM.

## What it does

- **Layer 1: deterministic statistical checks (always on).** Covers class imbalance, differential missingness, sensitive-column ↔ target correlation, and demographic-parity gaps. Same CSV in → same findings out.
- **Layer 2: optional LLM interpretation:** pass `task_description=...` and an LLM provider explains the evidence *on top of*, never instead of, Layer 1.
- **Shareable reports:** byte-reproducible markdown, HTML tables for Jupyter, PDFs with charts. Every finding carries severity, location, metric, and justification.
- **Jupyter-friendly:** a report on the last cell line renders as an HTML table; `report.to_dict()` gives a JSON snapshot.
- **Optional server and UI:** `pip install -e ".[server]"` (FastAPI), `".[ui]"` (Streamlit), `".[pdf]"` (PDF export).

## How it works

Statistics first, interpretation second. `audit()` runs Layer 1 checks against fixed thresholds, tags each finding with severity and an exact location (column, metric, sample size), and composes the report. Layer 2 reads only that evidence, so the LLM can't invent findings. Reports carry provenance (`generated_at`, provider/model, thresholds), so any audit is reproducible.

> **Severity is effect-size based, not significance-based.** Layer 1 runs no hypothesis tests: with small samples (e.g. the bundled 8-row example) a large gap or correlation carries wide sampling error. Treat findings as screening signals and validate on larger data before acting.

## Quick facts

| | |
| --- | --- |
| Language | Python ≥ 3.9 |
| Dependencies | pandas, numpy, scipy, scikit-learn, pydantic (core); extras for LLM, PDF, server, UI |
| Offline? | Yes: Layer 1 needs no network, accounts, or API keys |
| Interfaces | Library (`audit()`), optional FastAPI server, optional Streamlit UI |
| License | MIT |

## More

- Layer 2 providers: set `LAYER2_PROVIDER` (openai / openrouter / groq) plus its API key env var, or pass your own `BaseLLMClient` (see `examples/custom_llm_client.py`).
- Development: `pip install -e ".[dev]"`, then `pytest -m "not slow and not e2e"` and `ruff check src tests scripts`.
- [Versioned quickstart output](docs/examples/quickstart-result.md) · [Roadmap](docs/next-phase-roadmap.md) · [CHANGELOG](CHANGELOG.md) · [Publishing (maintainers)](.github/workflows/) via Trusted Publishing on release.
