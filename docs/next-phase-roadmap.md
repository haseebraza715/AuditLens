# AuditLens — Next-Phase Roadmap

**Status:** Post-refactor. Library exists, public API is shipped, tests pass.
**Goal of this document:** A concrete, phased execution plan that takes the project from "library on disk" to "library people actually adopt." Every phase has explicit deliverables, exit criteria, and an honest justification for why it exists.

---

## Guiding principles

Three rules that override every other decision in this document:

1. **Credibility before features.** A library with a green CI badge and 8 well-documented metrics beats a library with 30 undocumented metrics and no CI. Polish the foundation before adding capability.
2. **Compete on interpretation, not metric count.** AIF360 will always have more metrics. AuditLens wins on *contextual interpretation* + *workflow integration* (CLI, MCP, notebook). Stop benchmarking on metric depth.
3. **Synchronous-first.** The target user runs `audit()` in a notebook. Async job queues, multi-tenant servers, and dashboards are speculative until proven otherwise. Don't build them.

---

## Phase 1 — Make the refactor real (this weekend, ~4–6 hours)

**Why this exists:** Until the refactor is on GitHub with a working `pip install -e .`, everything else in this document is fiction. This phase has zero new features. It just turns the work into a real repository state.

### 1.1 Push the refactor to `main`

- Verify `pip install -e .` works in a clean venv.
- Verify `pytest tests/` passes (all 39 tests, plus any new ones from the refactor).
- Squash-merge or commit cleanly. Push to `main`.

**Exit criteria:** GitHub repo shows `src/auditlens/` layout, not `backend/`.

### 1.2 Pin dependency versions in `pyproject.toml`

Volatile packages need bounds. Without them, `pip install auditlens` will randomly break six months from now when LangGraph or Pydantic ships a breaking change.

```toml
dependencies = [
    "pandas>=1.5,<3.0",
    "numpy>=1.20,<3.0",
    "scipy>=1.7,<2.0",
    "scikit-learn>=1.0,<2.0",
    "pydantic>=2.0,<3.0",
    "langgraph>=0.2,<1.0",
    "langchain>=0.2,<1.0",
    "python-dotenv>=1.0,<2.0",
]

[project.optional-dependencies]
openai = ["openai>=1.0,<2.0", "langchain-openai>=0.1,<1.0"]
groq = ["groq>=0.9,<1.0"]
pdf = ["reportlab>=4.0,<5.0"]
viz = ["matplotlib>=3.5,<4.0"]
```

**Exit criteria:** Fresh venv install works. No upper-bound exclusions accidentally break the dependency resolver.

### 1.3 Polish `AuditLensReport` for notebook UX

The single moment that determines whether a notebook user trusts the library is when they evaluate `report` in a cell. Default `<AuditLensReport object at 0x...>` is unacceptable.

Add to the `AuditLensReport` class in `src/auditlens/api.py`:

```python
def __repr__(self) -> str:
    sev = self.summary.get("severity_counts", {})
    return (
        f"AuditLensReport(status={self.status!r}, "
        f"issues={len(self.issues)}, "
        f"severity={dict(sev)})"
    )

def _repr_html_(self) -> str:
    """Jupyter rich display."""
    rows = "".join(
        f"<tr><td>{i['issue_type']}</td><td>{i['severity']}</td><td>{i.get('description', '')[:80]}</td></tr>"
        for i in self.issues
    )
    return f"<table><tr><th>Type</th><th>Severity</th><th>Detail</th></tr>{rows}</table>"

def to_dict(self) -> dict:
    return {"status": self.status, "summary": self.summary, "issues": self.issues, ...}
```

**Exit criteria:** Evaluating `report` in Jupyter renders an HTML table. Plain Python repr is one readable line.

### 1.4 Verify and commit `notebook_quickstart.ipynb`

This is your most important marketing artifact. Anyone evaluating the library will open this notebook before deciding to `pip install`.

- Open it in Jupyter, run every cell top-to-bottom on a clean kernel.
- Add markdown cells between code cells explaining what's happening.
- Use the COMPAS dataset already in the repo (it's a well-known fairness teaching dataset — perfect for this).
- Keep it short: 6–8 cells max. Long notebooks lose people.

**Exit criteria:** Notebook renders cleanly on GitHub's notebook viewer. Reads like a tutorial, not a test script.

### 1.5 Repo hygiene

- Delete `bias_audit_mvp_plan.html` from repo root — internal planning artifact, makes the repo look messy.
- **Read** `AGENT.MD` first. If it's just internal notes, delete. If it has agent instructions used by Cursor/Claude/etc., move to `.cursorrules` or keep.
- Move all internal planning docs from `docs/` into a `docs/internal/` subfolder so the public-facing docs are clearly separated.
- Add `.auditlens_artifacts/` and `compas-scores-two-years.csv` to `.gitignore` if not already.

**Exit criteria:** Anyone landing on the GitHub repo sees a clean root with README, pyproject.toml, src/, tests/, examples/, docs/.

### 1.6 PyPI name reservation check

Before any further branding investment, run:

```bash
pip index versions auditlens
# or visit https://pypi.org/project/auditlens/
```

If `auditlens` is taken, decide on the alternative *now* (`auditlens-py`, `audit-lens`, `bias-auditlens`, etc.) and rename throughout the codebase before anything else gets shipped.

**Exit criteria:** Confirmed available name, or renamed before Phase 2.

---

## Phase 2 — Credibility & distribution channels (week 1, ~3 days)

**Why this exists:** A library with no CI badge, no CLI, and no MCP server is invisible. This phase adds the three signals that make AuditLens look like a real, adoptable tool *and* opens three distinct distribution channels (CI users, shell users, AI-assistant users).

### 2.1 GitHub Actions CI

Create `.github/workflows/ci.yml`:

```yaml
name: CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip
      - run: pip install -e ".[dev]"
      - run: pytest tests/ -q --tb=short
      - run: python -c "from auditlens import audit; print('import ok')"
```

Add the badge to README:

```markdown
![CI](https://github.com/haseebraza715/AuditLens/actions/workflows/ci.yml/badge.svg)
```

**Exit criteria:** Green badge on README. Tests pass on Python 3.9, 3.11, 3.12.

### 2.2 CLI entrypoint

Add to `pyproject.toml`:

```toml
[project.scripts]
auditlens = "auditlens.cli:main"
```

Create `src/auditlens/cli.py` (~100 lines using `argparse`):

```bash
# Layer 1 only (deterministic, no API key needed, fast)
auditlens audit data.csv --target income --sensitive race sex --stats-only

# Full pipeline with LLM interpretation
auditlens audit data.csv --target income --sensitive race \
  --task "predict creditworthiness" --provider openai

# Output formats
auditlens audit data.csv --target income --sensitive race --output report.md
auditlens audit data.csv --target income --sensitive race --output report.pdf
auditlens audit data.csv --target income --sensitive race --output report.json

# Exit codes for CI use
auditlens audit data.csv --target income --sensitive race --stats-only \
  --fail-on high   # exits 1 if any high-severity issue found
```

**Critical:** the `--stats-only` flag is the CI mode. Layer 2 is non-deterministic and costs money — it has no place in a CI pipeline. Document this clearly.

**Exit criteria:** `auditlens --help` works after `pip install -e .`. `--stats-only --fail-on high` exits 1 on the COMPAS dataset.

### 2.3 MCP server (`auditlens-mcp` extra)

This is the highest-leverage distribution play in late 2025 / 2026. Every Claude Code, Cursor, and Windsurf user is a potential AuditLens user the moment you ship an MCP server.

Add to `pyproject.toml`:

```toml
[project.optional-dependencies]
mcp = ["mcp>=0.9,<1.0"]

[project.scripts]
auditlens-mcp = "auditlens.mcp_server:main"
```

Create `src/auditlens/mcp_server.py`. Expose 3 tools:

| Tool | Purpose |
|---|---|
| `audit_csv` | Path to CSV + target/sensitive columns → returns Layer 1 issues JSON |
| `audit_csv_with_task` | Same as above + task description → runs Layer 2 |
| `list_supported_metrics` | Returns the catalog of available checks (helps the LLM decide what to ask for) |

The user experience: a data scientist in Claude Code says *"audit my training data for bias before I fit this classifier"* — Claude calls your MCP tool, gets structured findings, and surfaces them inline. Zero friction.

Document MCP install in README:

```bash
pip install auditlens[mcp]
# Add to ~/.config/claude-code/mcp.json:
{
  "mcpServers": {
    "auditlens": { "command": "auditlens-mcp" }
  }
}
```

**Exit criteria:** `auditlens-mcp` runs as a stdio MCP server. Tested manually with at least one MCP client (Claude Code or `mcp inspect`).

### 2.4 `CHANGELOG.md` and `v0.1.0-alpha` tag

Create `CHANGELOG.md` following Keep-a-Changelog format:

```markdown
# Changelog

## [0.1.0-alpha] - 2026-04-XX
### Added
- pip-installable `auditlens` package (src layout)
- Public API: `audit()` + `AuditLensReport`
- Layer 1 statistical checks: class distribution, missingness, correlation, demographic parity
- Layer 2 LLM interpretation via LangGraph (OpenAI, Groq, OpenRouter)
- Layer 3 report generation (Markdown, PDF)
- CLI: `auditlens audit ...` with `--stats-only` mode for CI pipelines
- MCP server: `auditlens-mcp` for Claude Code / Cursor integration
- Optional extras: `[openai]`, `[groq]`, `[pdf]`, `[viz]`, `[server]`, `[ui]`, `[mcp]`
```

Tag the release:

```bash
git tag -a v0.1.0-alpha -m "First public alpha"
git push origin v0.1.0-alpha
```

**Exit criteria:** GitHub releases page shows v0.1.0-alpha with the changelog as release notes.

---

## Phase 3 — Metric depth that actually matters (week 2, ~5 days)

**Why this exists:** The current 4 Layer 1 checks are too thin to credibly ship as a fairness tool. But adding 60 metrics to match AIF360 is the wrong battle. The goal is to add the **3 metrics that get asked about most** and **1 metric nobody else has**.

**Scope discipline:** This phase is data-only. Anything that requires model predictions (equalized odds, predictive parity, calibration) belongs in Phase 4 (`audit_model()`). Mixing them here causes scope creep.

### 3.1 Disparate impact ratio (the "80% rule")

```python
# src/auditlens/core/analyzers/disparate_impact.py

def analyze_disparate_impact(df, target_col, sensitive_cols):
    """
    Disparate impact ratio = P(Y=1 | sensitive=disadvantaged) / P(Y=1 | sensitive=privileged)

    The legal threshold (US EEOC "Four-Fifths Rule") is 0.8.
    A ratio below 0.8 is presumptive evidence of disparate impact.
    """
```

Why this metric: every compliance team in the US already knows it. It maps directly to legal precedent (Griggs v. Duke Power, EEOC Uniform Guidelines). Adding it makes AuditLens speak the same language regulators do.

Severity thresholds:
- `ratio >= 0.8` → low (passes the four-fifths rule)
- `0.6 <= ratio < 0.8` → medium
- `ratio < 0.6` → high

### 3.2 Intersectional subgroup analysis

The current `subgroup_analysis.py` analyzes one sensitive attribute at a time. Real-world bias often hits intersections (Black women, older Hispanic men, etc.) — a model can pass demographic parity for "race" and "sex" individually while catastrophically failing for the intersection.

Extend the existing analyzer in `src/auditlens/core/analyzers/subgroup_analysis.py`:

```python
def analyze_intersectional_subgroups(df, target_col, sensitive_cols, max_depth=2):
    """
    Compute outcome rates and gaps across all 2-way (and optionally 3-way) intersections
    of sensitive columns. Flag intersections where the gap exceeds a threshold AND the
    intersection has at least N samples (default 30) to avoid noise.
    """
```

This is genuinely differentiating. Most open-source fairness libraries either don't do this or require a lot of plumbing to set up. You give it for free.

### 3.3 Feature leakage / proxy detection

Detect when a non-sensitive feature is a near-perfect proxy for a sensitive attribute (the classic example: zip code → race).

```python
# src/auditlens/core/analyzers/feature_leakage.py

def analyze_feature_leakage(df, sensitive_cols, threshold=0.7):
    """
    For each non-sensitive feature, compute mutual information / Cramér's V
    against each sensitive column. Flag features that exceed `threshold` —
    these are proxies that will leak sensitive information into the model
    even if the sensitive column itself is dropped.
    """
```

Why this matters: this is the single most common "hidden bias" failure in industry. Teams remove the `race` column thinking they've solved the problem; the model learns it from `zip_code` anyway. None of the simple open-source tools surface this. AuditLens should.

This also gives Layer 2 something genuinely interesting to interpret: *"You dropped the `race` column, but `zip_code` has Cramér's V of 0.78 against `race`. Your model will likely still encode racial patterns."*

### 3.4 Distribution shift between train/test (optional, if time allows)

```python
def analyze_distribution_shift(train_df, test_df, sensitive_cols):
    """
    Detect whether the train/test split has materially different distributions
    of sensitive attributes (KS test for continuous, chi-square for categorical).
    """
```

This catches a sneaky failure mode where evaluation metrics look great but the test set isn't representative.

### 3.5 README positioning update

After Phase 3, **rewrite the comparison section of the README to stop competing on metric count**:

> **What AuditLens does that others don't:**
> - Contextual interpretation: don't just report a 0.13 demographic parity gap — explain why it's harmful for *your specific task*
> - Intersectional subgroups out of the box (race × sex, not just race and sex separately)
> - Proxy/feature-leakage detection
> - First-class CLI for CI pipelines (`--stats-only --fail-on high`)
> - MCP server for AI-assistant workflows (Claude Code, Cursor)

Do **not** include a metric-count comparison table. You will lose that comparison and shouldn't be playing on that field.

**Exit criteria:** 3 new analyzers shipped with tests. README rewritten. Layer 2 prompts updated to interpret the new issue types.

---

## Phase 4 — `audit_model()`: the EU AI Act unlock (week 3, ~5 days)

**Why this exists:** The EU AI Act, NYC Local Law 144, and most actual regulatory pressure focuses on **deployed models**, not raw datasets. Until AuditLens can audit a trained model's behavior on a test set, it's a dataset linter. With `audit_model()`, it becomes a compliance-adjacent tool.

This is your single largest competitive moat. Prioritize it over server work, async jobs, and PyPI publishing.

### 4.1 Public API design

```python
from auditlens import audit_model

report = audit_model(
    model,                    # any object with .predict() and optionally .predict_proba()
    X_test,                   # pd.DataFrame
    y_test,                   # pd.Series — ground truth labels
    sensitive_cols=["race", "sex"],
    task_description="loan approval",   # optional, triggers Layer 2
)
```

Critical design choices:
- Accept any model with `.predict()` — sklearn, XGBoost, PyTorch wrapper, custom callable
- `sensitive_cols` are columns *of `X_test`* — not separate arrays. Keeps the API simple.
- Returns the same `AuditLensReport` shape as `audit()` so users only learn one mental model

### 4.2 Add prediction-based analyzers

Now that predictions are available, add the metrics Phase 3 deliberately deferred:

| Metric | Module | What it measures |
|---|---|---|
| Equalized odds | `core/analyzers/equalized_odds.py` | TPR + FPR equality across groups |
| Equal opportunity | `core/analyzers/equal_opportunity.py` | TPR equality only (relaxed equalized odds) |
| Predictive parity | `core/analyzers/predictive_parity.py` | Precision equality across groups |
| Calibration gap | `core/analyzers/calibration.py` | Whether `predict_proba` is equally calibrated across groups |

Each has well-known thresholds in the fairness literature; reuse the same severity scheme.

### 4.3 Update Layer 2 prompts for model context

Layer 2 currently interprets dataset findings. When called from `audit_model()`, it now has predictions to reason about. Add a `context_type: "model"` field to the state and a model-specific prompt template:

> "This audit is of a *trained model's predictions on test data*, not raw training data. Frame recommendations accordingly: focus on threshold tuning, post-processing, model retraining with different objectives — not data collection or sampling."

**Exit criteria:** `audit_model(sklearn_classifier, X, y, sensitive_cols=[...])` returns a unified `AuditLensReport`. Layer 2 produces model-context recommendations. Tests cover at least one sklearn classifier end-to-end.

---

## Phase 5 — PyPI publish & lightweight docs (week 4, ~3 days)

**Why this exists:** "Pip-installable" is a lie until it's actually on PyPI. This phase makes the install command in the README literally true and adds the minimum docs needed for someone to learn the library without reading the source.

### 5.1 Publish to PyPI

Add `[build-system]` to `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

Build and publish:

```bash
python -m build
twine check dist/*
twine upload --repository testpypi dist/*   # smoke test first
twine upload dist/*                          # then real PyPI
```

Add badges to README:

```markdown
[![PyPI](https://img.shields.io/pypi/v/auditlens)](https://pypi.org/project/auditlens/)
[![Python](https://img.shields.io/pypi/pyversions/auditlens)](https://pypi.org/project/auditlens/)
[![License](https://img.shields.io/github/license/haseebraza715/AuditLens)](LICENSE)
```

**Exit criteria:** `pip install auditlens` works from a clean machine.

### 5.2 Documentation: README + notebook + 1 standalone guide

Skip MkDocs for now. It's a real maintenance burden and overkill for v0.1.0. Three docs are enough:

1. **`README.md`** — install, 10-line quickstart, link to notebook, link to API docs
2. **`examples/notebook_quickstart.ipynb`** — already exists from Phase 1.4
3. **`docs/api.md`** — every public function/class with parameters, return types, one-line example each

When you have real users asking docs questions, *then* invest in MkDocs. Premature documentation rots faster than premature code.

### 5.3 Anchor Layer 2 output to standards

Pure prompt engineering, no new code. Edit the recommend prompt in `src/auditlens/interpretation/prompts/`:

> "When recommending mitigations, where applicable, reference one of:
> - NIST AI RMF (e.g., 'Govern 1.1', 'Measure 2.11')
> - EU AI Act Article 10 (data and data governance) or Article 15 (accuracy, robustness)
> - IEEE 7003-2024 (algorithmic bias considerations)
> Cite the specific clause when relevant. Do not fabricate citations."

This single change converts AuditLens output from "interesting bias notes" to "compliance-aligned recommendations" — a difference that matters enormously to enterprise buyers and regulated industries.

**Exit criteria:** PyPI page exists. README has install + quickstart + badges. Layer 2 output references at least one standard per audit.

---

## Phase 6 — Workflow integration polish (month 2)

**Why this exists:** By now AuditLens is functional, deployable, and discoverable. This phase adds the ergonomic touches that turn "library people install" into "library people retweet."

### 6.1 pandas DataFrame accessor

```python
import auditlens  # registers the accessor as a side effect of import

df.auditlens.audit(target_col="income", sensitive_cols=["race", "sex"])
df.auditlens.summary()  # quick stats only
```

Implementation: `~30 lines using @pd.api.extensions.register_dataframe_accessor("auditlens")`.

Note the tradeoff: side-effect-on-import is mildly controversial (some users dislike it). Mitigate by also exposing the `audit()` function so users who object can ignore the accessor.

### 6.2 Pre-commit hook

Publish a `.pre-commit-hooks.yaml` in the repo root:

```yaml
- id: auditlens-audit
  name: AuditLens bias check
  entry: auditlens audit
  language: python
  types: [csv]
  args: [--stats-only, --fail-on, high]
```

Then teams can add to their `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/haseebraza715/AuditLens
    rev: v0.2.0
    hooks:
      - id: auditlens-audit
```

Caveat to investigate first: how many ML teams actually commit training data to git? If the answer is "very few," reframe this as a pre-merge GitHub Action template instead of a pre-commit hook. Same idea, more realistic delivery vehicle.

### 6.3 Reproducibility: seed and snapshot mode

Layer 2 LLM output is non-deterministic. For users who need reproducible audits (compliance, regulatory):

```python
report = audit(df, target_col=..., sensitive_cols=..., seed=42)
report.save_snapshot("audit_2026-04-18.json")

# Later, recreate the same report
loaded = AuditLensReport.load_snapshot("audit_2026-04-18.json")
```

`seed` controls Layer 1 ordering and passes `temperature=0` + `seed=42` to LLM clients that support it (OpenAI does, Groq mostly does).

### 6.4 Cost telemetry for Layer 2

Add to `AuditLensReport`:

```python
report.layer2_cost  # {"input_tokens": 1234, "output_tokens": 567, "estimated_usd": 0.012}
```

Users will ask. Showing the number proactively builds trust and lets people make informed decisions about CI integration.

**Exit criteria:** Accessor works. Pre-commit hook (or GitHub Action template) is documented. Reproducibility mode is tested. Cost telemetry surfaces in `__repr__`.

---

## Distribution plan (parallel to Phase 5–6)

Publishing to PyPI does not mean people will find the library. Active distribution moves:

| Channel | Action | When |
|---|---|---|
| **awesome-fairness lists** | Submit PRs to `awesome-machine-learning-fairness`, `awesome-responsible-ai`, etc. | After Phase 5 |
| **/r/MachineLearning** | Single high-quality post titled along the lines of "I built a CLI bias audit tool that integrates with Claude Code via MCP" | After Phase 5 |
| **HN Show HN** | One shot. Make it count. Lead with the MCP angle — that's currently novel. | After Phase 5 + 1 week of bug fixes |
| **Fairlearn / AIF360 communities** | Engage in their issue trackers / Slack. Don't promote — contribute. AuditLens should be seen as complementary, not competitive. | Ongoing |
| **ML Twitter / Bluesky** | Short demo video: COMPAS dataset → `auditlens audit` → report in 30 seconds. Embed in README too. | Phase 5 |
| **MCP directory** | Submit to the official MCP server registry once stable. | After Phase 2.3 lands |

**Anti-pattern to avoid:** writing a Medium post before Phase 2 ships. The first impression is the only one you get.

---

## Out of scope (deferred indefinitely)

These are real ideas that came up but should not happen in the next 8 weeks:

- **Async job queue / SQLite job store.** The server extra has no users yet. Don't engineer for hypothetical scale.
- **Multi-tenant SaaS.** Build adoption of the library first. SaaS without library users is a $0 ARR product.
- **Database UI / admin panel.** The Streamlit app is enough UI for v0.1.
- **Image / NLP model auditing.** Different problem domain. Different product. Not now.
- **Custom severity threshold UI.** Per-domain presets are interesting but solve a problem no user has reported yet.
- **Streaming / WebSocket audit progress.** Synchronous is fine for the dataset sizes the library targets.

---

## Timeline summary

| Phase | Duration | Outcome | Why this order |
|---|---|---|---|
| 1 | Weekend | Refactor real on GitHub, repo polished | Nothing else matters until this exists |
| 2 | 3 days | CI badge + CLI + MCP server + v0.1.0-alpha tag | Credibility + 3 distribution channels |
| 3 | 5 days | Disparate impact + intersectional + leakage detection | Closes data-side metric gap, adds genuine differentiation |
| 4 | 5 days | `audit_model()` + 4 prediction-based metrics | EU AI Act unlock + biggest competitive moat |
| 5 | 3 days | PyPI publish + README docs + standards anchoring | "Real library" status + enterprise alignment |
| 6 | Month 2 | Accessor + hook + reproducibility + cost telemetry | Polish that drives adoption |

**End state after Phase 5 (~3 weeks of focused work):**

- `pip install auditlens` works
- Green CI badge
- CLI usable in CI pipelines
- MCP server usable in Claude Code / Cursor
- 7 statistical checks (4 data + 3 prediction) plus feature leakage and intersectionality
- Layer 2 references NIST/EU AI Act standards
- v0.1.0 release on PyPI and GitHub
- A real notebook tutorial people can run

That's the version that gets adoption.

---

## What "done" looks like for v1.0 (north star, not commitment)

To prevent scope drift in subsequent phases, here's the explicit definition of when AuditLens is "done" enough to declare v1.0:

- 1000+ PyPI downloads/month
- Used in at least 3 public GitHub repos as a dependency
- At least one cited compliance use case (NIST/EU AI Act/NYC LL144)
- Zero-config audit works for any pandas DataFrame
- MCP server listed in the official MCP registry
- README is the canonical fairness library landing page for the LLM-augmented angle

Anything beyond this is a v2.0 conversation. The temptation to add features before achieving the v1.0 bar is the single biggest risk to this project — guard against it deliberately.
