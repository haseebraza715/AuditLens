# Evidence: UCI Adult (Census Income) Layer 1 audit

This directory is AuditLens's real-data evidence. It records the deterministic
Layer 1 statistical audit of the public UCI Adult (Census Income) dataset, the
most commonly used fairness/ML benchmark table. Nothing here involves a model,
an LLM, the network, or an API key.

Artifacts:

- `adult-income-report.json` - JSON snapshot of `report.to_dict()`. Floats are
  rounded to 6 decimal places for cross-version byte stability. Byte-stable:
  same input CSV produces the same bytes on every run.
- `adult-income-report.md` - the same findings as human-readable markdown with
  a provenance header; the body is exactly `report.to_markdown()`.

Regenerate both with:

```bash
.venv/bin/python scripts/evidence_adult.py
```

The script verifies the fixture SHA-256 before writing anything. Tests in
`tests/integration/test_adult_golden.py` re-run the audit, compare against
these committed bytes, and pin the SHA-256.

## Dataset provenance and license

- Source: UCI Machine Learning Repository, "Adult" (Census Income) data set.
  https://archive.ics.uci.edu/dataset/2/adult
- Origin: extracted from the 1994 US Census Bureau database.
- License: Creative Commons Attribution 4.0 International (CC BY 4.0), as
  stated on the UCI dataset page.
- Citation: Becker, B. & Kohavi, R. (1996). *Adult* [Dataset]. UCI Machine
  Learning Repository. https://doi.org/10.24432/C5XW20.
- Vendored file: `tests/fixtures/adult.data` (32,561 rows).
- Fixture SHA-256:
  `5b00264637dbfec36bdeaab5676b0b309ff9eb788d63554ca0a249491c86603d`

## Schema

Headerless, space-separated CSV with `?` encoding missing values, read via:

```python
pd.read_csv(path, header=None, names=ADULT_COLUMNS, skipinitialspace=True, na_values="?")
```

Columns: `age`, `workclass`, `fnlwgt`, `education`, `education_num`,
`marital_status`, `occupation`, `relationship`, `race`, `sex`,
`capital_gain`, `capital_loss`, `hours_per_week`, `native_country`, `income`.

Audit configuration: target `income` (`<=50K` / `>50K`); sensitive columns
`sex` and `race`. `workclass`, `occupation`, and `native_country` contain
missing values.

## Interpretation boundary

These findings are **effect-size screening signals**, not significance tests
and not evidence of causality. Layer 1 runs no hypothesis tests and no
confidence intervals; severity is a fixed magnitude cutoff
(`SEVERITY_THRESHOLDS`). Some sensitive subgroups are small, so estimates
carry sampling error. Validate on task-specific data before acting.

Known findings (magnitudes verified by `tests/integration/test_adult_golden.py`):

- `class_imbalance_income`: high, imbalance ratio about 3.15:1 (`<=50K` majority).
- `demographic_parity_sex_income`: high, positive-rate gap about 0.20
  (male about 0.31 vs female about 0.11).
- `demographic_parity_race_income`: high, positive-rate gap about 0.17.
- `correlation_sex_income` / `correlation_race_income`: medium, Cramer's V
  about 0.22 / 0.10.
- `missingness_gap_race_native_country`: medium, missingness gap about 0.08.
