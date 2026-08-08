# AuditLens evidence: UCI Adult (Census Income), Layer 1 statistical audit

Deterministic Layer 1 audit. No LLM, no network, no API keys.

## Dataset

- Source: UCI Machine Learning Repository, 'Adult' (Census Income)
- URL: https://archive.ics.uci.edu/dataset/2/adult
- License: Creative Commons Attribution 4.0 International (CC BY 4.0). Cite Becker & Kohavi (1996), DOI 10.24432/C5XW20.
- Rows: 32561
- Fixture SHA-256: `5b00264637dbfec36bdeaab5676b0b309ff9eb788d63554ca0a249491c86603d`
- Target: `income` (`<=50K` / `>50K`)
- Sensitive columns: `sex, race`
- Columns: age, workclass, fnlwgt, education, education_num, marital_status, occupation, relationship, race, sex, capital_gain, capital_loss, hours_per_week, native_country, income
- Evidence format: `adult-layer1-v1`

## Interpretation boundary

These findings are **effect-size screening signals**, not significance
tests and not evidence of causality. Layer 1 runs no hypothesis tests
and no confidence intervals; severity is a fixed magnitude cutoff
(`SEVERITY_THRESHOLDS`). With some sensitive subgroups the underlying
sample sizes are small, so estimates carry sampling error. Validate on
task-specific data before drawing conclusions.

## Regeneration

    .venv/bin/python scripts/evidence_adult.py

The JSON artifact rounds floats to 6 decimal places for cross-version
byte stability; the markdown body below is exactly `report.to_markdown()`.

---
# AuditLens statistical audit (Layer 1)

- Rows: `32561`
- Columns: `15`
- Target: `income`
- Sensitive columns: `sex, race`

## Summary

- Total issues: `6`
- High severity: `3`
- Medium severity: `3`
- Low severity: `0`

## Findings

### 1. `class_imbalance_income` (class_imbalance)

- Severity: **HIGH**
- Target column 'income' has imbalance ratio of 3.153:1

### 2. `demographic_parity_race_income` (demographic_parity_gap)

- Severity: **HIGH**
- Demographic parity gap for 'race' is 0.173 for target 'income'

### 3. `demographic_parity_sex_income` (demographic_parity_gap)

- Severity: **HIGH**
- Demographic parity gap for 'sex' is 0.196 for target 'income'

### 4. `correlation_race_income` (sensitive_correlation)

- Severity: **MEDIUM**
- Correlation score between sensitive column 'race' and target 'income' is 0.101

### 5. `correlation_sex_income` (sensitive_correlation)

- Severity: **MEDIUM**
- Correlation score between sensitive column 'sex' and target 'income' is 0.216

### 6. `missingness_gap_race_native_country` (differential_missingness)

- Severity: **MEDIUM**
- Missingness differs by 0.080 for 'native_country' across 'race' groups


_Layer 2 interpretation was not run. Pass `task_description` to enable LLM-assisted reporting._
