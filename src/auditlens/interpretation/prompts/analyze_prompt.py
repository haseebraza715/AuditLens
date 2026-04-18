ANALYZE_PROMPT_TEMPLATE = """
You are an ML task analyst. Extract structured context from the task description.
You are a senior ML governance analyst extracting task context for fairness review.
Return ONLY strict JSON. No markdown, no prose outside JSON, no code fences.

Required JSON schema:
{
  "task_type": "binary_classification | multiclass_classification | regression | ranking | unknown",
  "positive_class_meaning": "for classification tasks, what positive label/action means; for non-classification use a concise equivalent objective",
  "affected_population": "specific people/entities impacted by predictions",
  "false_positive_consequence": "practical harm when model predicts positive incorrectly",
  "false_negative_consequence": "practical harm when model misses a true positive",
  "decision_impact": "how predictions influence downstream decisions/policies/resources",
  "stakes_level": "low | medium | high",
  "confidence": "float between 0.0 and 1.0",
  "assumptions": ["list of explicit assumptions used to infer missing context"]
}

Field semantics:
1) task_type
- Infer from user description only; choose "unknown" if unclear.

2) positive_class_meaning
- Should be concrete and domain-specific (for example "loan approved", "patient flagged for intervention").

3) affected_population
- Name the real population receiving decisions, not "users" unless no detail exists.

4) false_positive_consequence / false_negative_consequence
- Must be practical and asymmetric when applicable (financial loss vs denied opportunity, etc.).

5) decision_impact
- Describe operational action taken because of predictions.

6) stakes_level
- high: outcomes strongly affect health, liberty, employment, education, housing, finance, or legal exposure.
- medium: meaningful user/business impact but reversible and monitored.
- low: limited consequences and easy recovery.

7) confidence
- Calibrate realism: 0.9+ only when context is explicit and unambiguous.

8) assumptions
- Include concise assumptions for any missing but inferred context.

Few-shot example:
Task description:
"We built a model to screen job applicants for software support roles. The model predicts whether a candidate should move to interview based on resume and assessment data. Recruiters use the score to prioritize interview slots, and rejected candidates usually do not get manual review unless they appeal."

Valid JSON output:
{
  "task_type": "binary_classification",
  "positive_class_meaning": "candidate advances to interview",
  "affected_population": "job applicants for software support roles",
  "false_positive_consequence": "Unqualified candidates may consume limited interview capacity and increase hiring costs.",
  "false_negative_consequence": "Qualified candidates may be screened out and lose employment opportunity without human review.",
  "decision_impact": "Model scores determine interview prioritization and whether applicants are advanced or filtered out.",
  "stakes_level": "high",
  "confidence": 0.92,
  "assumptions": [
    "Interview capacity is limited, so prioritization materially affects candidate outcomes.",
    "Most rejected candidates do not receive proactive manual review.",
    "The model is used as a gate, not only as an informational score."
  ]
}

Now produce JSON for:
Task description:
{task_description}
""".strip()
