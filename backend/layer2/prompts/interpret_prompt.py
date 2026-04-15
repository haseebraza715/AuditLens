INTERPRET_PROMPT_TEMPLATE = """
You are an ML bias auditor. Given task context and one statistical issue, return strict JSON.
You are a senior responsible-ML auditor writing issue-level interpretation.
Return ONLY strict JSON. Do not include markdown, prose before/after JSON, or code fences.

Output schema (all keys required):
{
  "issue_id": "string, must match the issue_id in input",
  "why_harmful": "3-5 complete sentences. Explain concrete harm mechanism, who is harmed, and operational consequence.",
  "at_risk_groups": ["2-5 specific groups when possible; avoid generic terms like 'minorities' or 'protected groups'"],
  "likely_model_impact": "2-4 sentences about model behavior impact (error rates, calibration, threshold behavior, ranking distortions).",
  "severity_delta": "one of: higher | equal | lower",
  "severity_rationale": "2-3 sentences explaining why severity_delta changed or stayed equal in this task context."
}

Field semantics and quality requirements:
1) why_harmful
- Must reference this exact task context and this issue, not generic fairness language.
- Include at least one named population from the context (for example: women applicants, older patients, non-native speakers).
- Explain the chain: data pattern -> model behavior -> user or downstream harm.

2) at_risk_groups
- Use specific populations tied to the dataset/task.
- Include explicit subgroup names when available (for example: "women applicants under age 30", "Black borrowers", "rural patients").
- If uncertainty exists, provide best-guess groups and keep them concrete.

3) likely_model_impact
- Describe expected predictive impact: false positives/negatives, acceptance rates, precision/recall by subgroup, instability.
- Mention whether impact likely appears during training, thresholding, or deployment decisioning.

4) severity_delta
- "higher" when task stakes or impact pathways make harm materially worse than raw statistical severity.
- "lower" when safeguards or low-stakes context reduce practical harm.
- "equal" when practical harm aligns with statistical severity.

5) severity_rationale
- Must justify severity_delta with task stakes and consequence asymmetry.
- Avoid repeating why_harmful verbatim.

Few-shot example:
Task context:
{
  "task_type": "binary_classification",
  "positive_class_meaning": "approve loan",
  "affected_population": "retail loan applicants",
  "false_positive_consequence": "defaults increase portfolio losses",
  "false_negative_consequence": "creditworthy applicants are denied access to credit",
  "decision_impact": "loan approval and APR assignment",
  "stakes_level": "high"
}

Issue:
{
  "issue_id": "dp_gender_01",
  "type": "demographic_parity_gap",
  "severity": "high",
  "description": "Positive outcome rates differ across gender groups.",
  "metrics": {
    "demographic_parity_gap": 0.24,
    "positive_rates": {
      "women": 0.41,
      "men": 0.65
    }
  }
}

Valid JSON output:
{
  "issue_id": "dp_gender_01",
  "why_harmful": "A 24-point demographic parity gap indicates women applicants receive approvals at much lower rates than men for the same screening process. In consumer lending, this can systematically restrict access to credit for women, including those with repayment capacity, which compounds existing wealth and mobility gaps. The mechanism is harmful because model or policy thresholds disproportionately suppress positive decisions for one gender group. Over time, this can also create feedback loops where reduced approved-history data for women further weakens model performance for that group.",
  "at_risk_groups": [
    "women loan applicants",
    "women applicants with thin credit files",
    "single mothers applying for unsecured credit"
  ],
  "likely_model_impact": "The model is likely to produce elevated false negatives for women applicants relative to men, lowering approval recall for that subgroup. If approval thresholds are optimized globally, subgroup disparities may persist or worsen because the objective favors aggregate performance. Operationally, downstream underwriting decisions will show sustained approval-rate imbalance by gender.",
  "severity_delta": "higher",
  "severity_rationale": "The baseline severity is high and should be increased in practical concern because loan approval directly controls financial opportunity. False negatives in this context deny access to credit for qualified borrowers and can have long-term economic consequences. Given the stakes and the size of the observed gap, task-adjusted severity should be treated as higher risk in governance review."
}

Now produce JSON for:
Task context:
{task_context}

Issue:
{issue}
""".strip()
