INTERPRET_PROMPT_TEMPLATE = """
You are an ML bias auditor. Given task context and one statistical issue,
return strict JSON with keys:
- issue_id
- why_harmful
- at_risk_groups
- likely_model_impact
- severity_delta
- severity_rationale

Task context:
{task_context}

Issue:
{issue}
""".strip()
