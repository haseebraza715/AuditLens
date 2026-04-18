# AuditLens

AuditLens runs **deterministic statistical checks** (Layer 1) and optional **LLM-assisted interpretation** (Layer 2) on tabular datasets, then builds **shareable reports** (Layer 3). It is designed for notebooks and Python scripts: install the core library, call `audit()`, and optionally add extras for PDF charts, HTTP API, or Streamlit UI.

## Quickstart (library)

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
```

```python
from auditlens import audit
import pandas as pd

df = pd.read_csv("compas-scores-two-years.csv")  # or your own CSV
report = audit(
    df,
    target_col="two_year_recid",
    sensitive_cols=["race", "sex"],
)
print(report.summary)       # severity counts (dict)
print(len(report.issues))   # structured AuditIssue list
print(report.to_markdown()[:500])
```

In **Jupyter**, put `report` on the last line of a cell to render an **HTML table** (`_repr_html_()`). In any REPL, `repr(report)` is a short one-line summary, and `report.to_dict()` returns a JSON-friendly snapshot.

- **Layer 1 only (default install):** omit `task_description` or pass `None`. You still get `summary`, `issues`, and a short Layer 1 markdown report from `to_markdown()`.
- **Layer 2:** set a non-empty `task_description` and install an LLM extra (for example `pip install -e ".[openai]"`), configure provider env vars, or pass a `BaseLLMClient` instance as `llm_client` (see `examples/custom_llm_client.py`).
- **PDF:** `report.to_pdf("report.pdf")` requires `pip install -e ".[pdf]"` (includes ReportLab and matplotlib for charts).

### Optional install extras

| Extra | Purpose |
| --- | --- |
| *(core only)* | Layer 1, schemas, `audit()` without LLM |
| `openai` | LangGraph + LangChain + OpenAI SDK for Layer 2 |
| `groq` / `openrouter` | Same stack as `openai` (OpenAI-compatible clients) |
| `pdf` | ReportLab + matplotlib for `to_pdf()` |
| `viz` | matplotlib only (charts / `visualizations` module) |
| `server` | FastAPI + Uvicorn HTTP API |
| `ui` | Streamlit app (pulls in `server`) |
| `all` | All of the above |
| `dev` | pytest, httpx, and extras needed for the test suite |

## Configuration (Layer 2 providers)

With `openai` (or `server` / `ui`) installed, set provider environment variables, for example:

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

## Optional HTTP API (`server` extra)

```bash
python3 -m pip install -e ".[server]"
python3 -m uvicorn auditlens_server.app:app --reload --env-file .env
```

Endpoints include `POST /upload`, `POST /analyze`, `POST /analyze-task`, report routes, and async jobs (unchanged from the previous FastAPI app).

## Optional Streamlit UI (`ui` extra)

```bash
python3 -m pip install -e ".[ui]"
python3 -m streamlit run ui/auditlens_ui/app.py
```

Or use `./run-dev.sh` after installing `.[ui]` into `.venv`.

## Documentation layout

- **[`docs/next-phase-roadmap.md`](docs/next-phase-roadmap.md)** — phased adoption plan (CI, CLI, MCP, PyPI, etc.).
- **[`examples/notebook_quickstart.ipynb`](examples/notebook_quickstart.ipynb)** — short COMPAS tutorial (run top-to-bottom in a clean kernel).
- **[`docs/internal/`](docs/internal/)** — archived planning notes (MVP plan, layer phase write-ups).

### Install from PyPI

After the first release is uploaded:

```bash
pip install auditlens
pip install "auditlens[openai]"   # Layer 2 + PDF/UI extras as needed
```

### Publish to PyPI (maintainers)

The repo includes GitHub Actions workflows under **`.github/workflows/`**:

| File | Purpose |
| --- | --- |
| [`ci.yml`](.github/workflows/ci.yml) | Runs tests on Python 3.9 / 3.11 / 3.12 on every push and PR to `main`. |
| [`publish-pypi.yml`](.github/workflows/publish-pypi.yml) | Builds and publishes to PyPI using **Trusted Publishing** (OIDC — no long-lived PyPI token in GitHub secrets). |

#### Trusted Publishing (recommended)

1. On **PyPI**: create the `auditlens` project → **Manage** → **Publishing** → add a **pending** trusted publisher:
   - **PyPI project name:** `auditlens`
   - **Owner / repository:** your GitHub org or user + `AuditLens`
   - **Workflow name:** `publish-pypi.yml` (this is the **filename** only; PyPI may show it as `.github/workflows/publish-pypi.yml` depending on the form)
   - **Environment name:** `pypi` (must match the `environment: name: pypi` job in the workflow)

2. On **GitHub**: repo **Settings → Environments → New environment** → name it **`pypi`** (no secrets required for OIDC).

3. Merge these workflow files to **`main`**, then on PyPI confirm the **pending** publisher (PyPI verifies against a successful workflow run).

4. **Publish:** create a [GitHub Release](https://github.com/haseebraza715/AuditLens/releases) and publish it (or run the workflow manually via **Actions → Publish to PyPI → Run workflow**). The release event triggers `publish-pypi.yml`, which runs `python -m build` and uploads `dist/*`.

5. Keep **`version`** in `pyproject.toml` in sync with the release tag you expect (e.g. tag `v0.1.0` matches `version = "0.1.0"`).

#### Manual upload (token fallback)

The wheel and sdist build cleanly (`python -m build`; `twine check dist/*` passes). From a machine with credentials:

```bash
python3 -m pip install build twine
python3 -m build
python3 -m twine check dist/*
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-YOUR_TOKEN_HERE
python3 -m twine upload dist/*
```

## Development

```bash
python3 -m pip install -e ".[dev]"
python3 -m pytest tests/
```

### Phase 1 release checklist (manual)

1. Clean venv: `python3 -m venv .venv && source .venv/bin/activate && pip install -e . && pytest tests/ -q`
2. Commit and **push to `main`** so GitHub shows the `src/auditlens/` layout.

See `examples/notebook_quickstart.ipynb` for a notebook-oriented walkthrough.

## Layout

- `src/auditlens/` — installable package (`core`, `interpretation`, `reporting`, public `audit()` API)
- `server/auditlens_server/` — FastAPI app (optional extra)
- `ui/auditlens_ui/` — Streamlit UI (optional extra)
- `tests/` — unit, integration, and smoke tests by area

**What `pip install auditlens` ships:** only the Python packages discovered under `src/`, `server/`, and `ui/` (see `pyproject.toml`). Tests, notebooks, and markdown docs stay in the **GitHub** repo for developers; they are not bundled into the wheel unless you add them explicitly.
