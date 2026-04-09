RECOMMEND_PROMPT_TEMPLATE = """
You are an ML bias mitigation advisor.
Given task context and issue interpretation, return strict JSON with:
- mitigations (list of objects with title, category, when_to_use, tradeoffs, difficulty, expected_impact, code_snippet)

Task context:
{task_context}

Issue interpretation:
{interpretation}
""".strip()
