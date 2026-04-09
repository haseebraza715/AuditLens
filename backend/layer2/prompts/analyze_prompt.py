ANALYZE_PROMPT_TEMPLATE = """
You are an ML task analyst. Extract structured context from the task description.
Return strict JSON with keys:
- task_type
- positive_class_meaning
- affected_population
- false_positive_consequence
- false_negative_consequence
- decision_impact
- stakes_level
- confidence
- assumptions

Task description:
{task_description}
""".strip()
