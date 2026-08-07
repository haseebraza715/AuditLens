# Reproducible quickstart example

This artifact records the deterministic Layer 1 example shipped in the README.

- Input: `examples/quickstart.csv` (synthetic, CC0-1.0)
- Input SHA-256: `f63570b45c870afb874ae39eb2b366e30f5a170b4fc4b3c0bf4c59172a43df68`
- Producer: the literal Python snippet in `README.md` under "Quickstart (library)"
- Package base commit: `383830765c4ae0df57eb7b76b24719af9e2e9a35`
- Network/model use: none
- Expected status: complete

The output below is regenerated and compared in CI by
`tests/core/test_quickstart_artifact.py`, which also verifies the input hash.
Because Layer 1 never touches a model or the network, the markdown below is
byte-for-byte reproducible from the bundled CSV.

## Printed summary and issue count

```python
print(report.summary)
# {'total_issues': 2, 'high_severity': 2, 'medium_severity': 0, 'low_severity': 0}

print(len(report.issues))
# 2
```

## Full Layer 1 markdown report

```markdown
# AuditLens statistical audit (Layer 1)

- Rows: `8`
- Columns: `4`
- Target: `target`
- Sensitive columns: `group, sex`

## Summary

- Total issues: `2`
- High severity: `2`
- Medium severity: `0`
- Low severity: `0`

## Findings

### 1. `correlation_sex_target` (sensitive_correlation)

- Severity: **HIGH**
- Correlation score between sensitive column 'sex' and target 'target' is 0.500

### 2. `demographic_parity_sex_target` (demographic_parity_gap)

- Severity: **HIGH**
- Demographic parity gap for 'sex' is 0.500 for target 'target'


_Layer 2 interpretation was not run. Pass `task_description` to enable LLM-assisted reporting._
```

## Issue detail

| issue_id | type | severity | metric | value |
| --- | --- | --- | --- | --- |
| `correlation_sex_target` | `sensitive_correlation` | high | point-biserial `|r|` (n=8) | 0.500 |
| `demographic_parity_sex_target` | `demographic_parity_gap` | high | positive-rate gap (F=0.25 vs M=0.75, Δ) | 0.500 |

Notes:

- The "positive" class is resolved to `1` (the minority class; on a tie the
  conventional positive label `1` wins over `0`).
- Severity is effect-size based (see `SEVERITY_THRESHOLDS`); with n=8 the
  effect sizes are large, but the estimates have wide sampling error and are
  not significance-gated. Treat them as screening signals, not proof.
