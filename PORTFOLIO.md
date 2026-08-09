# AuditLens — portfolio summary

Deterministic, statistical bias and fairness auditing for tabular ML datasets: same CSV in, same findings out — with severity, reports, and an optional LLM read that can never invent evidence.

## CV bullets

- **Problem:** Fairness claims in ML are usually asserted from black-box model scores that no one can regenerate or audit. Built AuditLens so a dataset's bias surface is computed by deterministic statistical checks with fixed thresholds — reproducible, explainable, and inspectable before any LLM is involved.
- **Engineering:** Designed a layered pipeline (analyzers → severity → reports) where the optional LLM layer reads only precomputed statistics, hardened edge cases that silently corrupt audits (non-finite metrics rejected instead of labeled "low", Cramér's V clamped to [0,1], constant columns reported as undefined-not-zero, JSON-safe `inf→null` serialization), and made PDFs byte-reproducible via ReportLab `invariant=True`.
- **Evidence:** 342 tests green (`pytest tests`) including a synthetic known-bias dataset that plants findings and asserts the audit detects exactly them, plus a byte-locked golden regression on the 32,561-row UCI Adult dataset; `ruff check .` clean; shipped as a pip package with a CLI, FastAPI server, and Streamlit UI.

## 15-second explanation

AuditLens runs fixed statistical checks — class imbalance, differential missingness, sensitive-column/target correlations, demographic-parity gaps — over any tabular CSV, tags every finding with a severity and its exact metric, and writes shareable markdown/HTML/JSON/PDF reports. It is fully offline and deterministic: the same CSV always produces the same findings, so it is evidence you can audit, not a number you have to trust. An optional LLM layer explains findings on top of the statistics, never instead of them.

## 45-second explanation

Two layers, deliberately ordered. Layer 1 is a deterministic statistical audit: four analyzers (class distribution, missingness by group, correlations using Cramér's V / point-biserial / Spearman-Pearson, subgroup parity) run against fixed thresholds and emit issues with `high/medium/low` severity, the metric value, and a justification. Reports carry provenance — thresholds, provider, model — and the PDF export is byte-reproducible for identical inputs.

The design hardens the failure modes that quietly corrupt audits: non-finite metrics raise instead of becoming "low", Cramér's V is clamped to [0,1] with explicit NaN conventions, and `to_dict()` emits `inf`/`NaN` as `null` so any JSON consumer is safe. Layer 2 (optional) is an LLM graph that receives only the Layer 1 evidence, so it can adjust severity and explain harm but cannot invent findings; providers are OpenAI/Groq/OpenRouter via env-driven config.

The system ships three surfaces from one core: a CLI (`auditlens audit` / `auditlens report`), a library API (`audit(df, ...)` with a Jupyter HTML repr), and an optional FastAPI server with a Streamlit UI. Validation is evidence-forward: 342 tests, a synthetic dataset with planted bias used as a regression ground truth, and a golden lock on the UCI Adult audit (32,561 rows, byte-stable JSON/markdown).

## Difficult staff-engineer questions (with answers grounded in the code)

**Q1. What happens when a sensitive subgroup has zero rows (all-missing subgroup), and how does that differ between analyzers?**

In `analyze_missing_values_by_group` (src/auditlens/core/analyzers/missing_values.py) each group's `group_size` is checked before computing a missingness rate; groups with zero rows are skipped, and if fewer than two groups have computable rates the check is skipped entirely — no fabricated rates, no division by zero. `analyze_subgroup_label_distribution` (subgroup_analysis.py) does the same for parity rates, and adds a guard: if fewer than two groups remain, no issue is emitted. The correlation analyzer goes further: `_clean_pair` drops rows with NaN/inf in either column before any statistic, and requires at least 3 clean rows. So an all-missing subgroup never crashes an audit and never produces a bogus "no gap" finding — the convention is that a rate that cannot be computed is not evidence of anything.

**Q2. Why is Cramér's V clamped to [0, 1], and what does the clamp hide?**

Cramér's V is `sqrt(chi2 / (n * (min(r,c) - 1)))`, mathematically bounded by [0,1], but on small contingency tables chi2 can exceed its theoretical maximum, pushing V above 1. The clamp (`_cramers_v` in correlations.py) keeps the score in its defined range so severity thresholds (`cramers_v`: medium 0.1, high 0.3) stay meaningful. The same function makes two explicit NaN conventions: `chi2_contingency` emits inf/nan when cells have zero expected counts — that table is perfectly determined, so the score is 1.0, not 0.0; and degenerate tables (fewer than two categories on either axis) score 0.0 because the statistic is undefined. The clamp hides nothing: a clamped 1.0 means "the largest association this dataset can express", which is exactly the semantics severity wants. What the code deliberately does NOT do is silently treat an undefined statistic as zero evidence — that path raises instead (see Q4).

**Q3. What makes the PDF byte-reproducible, and what could still break it?**

`build_pdf_report` (reporting/generator.py) constructs ReportLab's `SimpleDocTemplate` with `invariant=True`, which suppresses the embedded creation timestamp that ReportLab normally writes into the xref/Info dictionary — the single biggest source of byte drift. Charts are matplotlib PNGs rendered from the same Layer 1 aggregations, and the issue list is processed in the sorted order produced by `sort_issues`. So identical inputs → identical PDF bytes, verified by tests. What could still break it: the PDF embeds no timestamps but chart PNGs depend on matplotlib's exact version (font rendering and anti-aliasing can differ across versions), and ReportLab internals can change byte layout across releases. CI does not pin either, so byte-reproducibility is guaranteed for a fixed environment, not across arbitrary upgrades — the honest reading of the promise.

**Q4. How is severity calibrated, and how do you know it is right?**

Severity is calibrated by effect-size thresholds, not significance: a single table in `config.py` (`SEVERITY_THRESHOLDS`) maps each metric to `medium`/`high` bounds — imbalance ratio 1.5/3.0, Cramér's V 0.1/0.3, demographic-parity gap and differential missingness 0.05/0.15. `score_threshold_metric` (core/severity.py) emits the metric value and the exact threshold comparison as the justification, so no finding is a bare label. Two properties make it trustworthy: it is config surface, not magic (users can pass their own table, validated up front for finite, ordered bounds), and it is deliberately honest about being uncalibrated to any downstream task — the README documents findings as screening signals, not causal claims. The one hard invariant: a non-finite metric raises `AuditLensError` instead of defaulting to "low", so a broken computation can never quietly pass an audit.

**Q5. How do you test a promise of determinism, and where would the promise break first?**

Three locks. `tests/core/test_quickstart_artifact.py` pins the SHA-256 of `examples/quickstart.csv` and asserts the audit's summary, metrics, and full markdown are byte-exact against the committed `docs/examples/quickstart-result.md`. `tests/integration/test_synthetic_bias.py` plants a known imbalance in a synthetic dataset and asserts the audit finds exactly the planted findings at the expected severities — ground truth for the detector itself. `tests/integration/test_adult_golden.py` locks the 32,561-row Adult audit to byte-stable JSON/markdown via `scripts/evidence_adult.py`. The promise would break first in the float layer: chi2 and Spearman results can differ at the last digit across numpy/scipy versions, and `pd.crosstab` column order is normalized but pandas-version-sensitive in edge cases. Markdown is pure string formatting (robust); PDF bytes additionally depend on matplotlib/ReportLab versions (see Q3). That is why the golden tests run in CI on every PR — they make any determinism regression visible immediately, not at release time.
