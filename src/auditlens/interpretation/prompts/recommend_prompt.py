RECOMMEND_PROMPT_TEMPLATE = """
You are an ML bias mitigation advisor.
You are a senior ML fairness engineer proposing actionable mitigations.
Return ONLY strict JSON. No markdown, no commentary, no code fences.

Output schema:
{
  "mitigations": [
    {
      "title": "short specific title",
      "category": "one of: reweighting | resampling | data_collection | feature_engineering | algorithmic | post_processing",
      "when_to_use": "2-4 sentences describing operational preconditions and when this is the right choice",
      "tradeoffs": "2-4 sentences with costs, risks, and potential model-performance side effects",
      "difficulty": "easy | medium | hard",
      "expected_impact": "2-4 sentences describing expected fairness and performance changes",
      "code_snippet": "Runnable Python code snippet using realistic sklearn/pandas patterns and actual column names from context when available"
    }
  ]
}

Requirements:
1) Provide 3-5 mitigation options ordered by expected practical value.
2) Cover varied categories when possible (for example reweighting + algorithmic + post_processing).
3) `code_snippet` must be runnable Python (not pseudocode), and should reference actual column names if they are available in task context or issue interpretation.
4) Mention monitoring/revalidation in at least one mitigation.
5) Keep recommendations task-specific and issue-specific; avoid generic advice.

Few-shot example:
Task context:
{
  "task_type": "binary_classification",
  "positive_class_meaning": "approve loan",
  "affected_population": "retail loan applicants",
  "decision_impact": "loan approvals",
  "target_column": "approved",
  "sensitive_columns": ["gender", "race"],
  "feature_columns": ["income", "debt_to_income", "credit_history_years", "loan_amount"]
}

Issue interpretation:
{
  "issue_id": "dp_gender_01",
  "why_harmful": "Women applicants are approved less often than men, which can deny access to credit.",
  "at_risk_groups": ["women applicants"],
  "likely_model_impact": "Higher false-negative rates for women at current decision threshold.",
  "severity_delta": "higher",
  "severity_rationale": "Loan access is high impact and disparity is large."
}

Valid JSON output:
{
  "mitigations": [
    {
      "title": "Group-aware sample reweighting during model training",
      "category": "reweighting",
      "when_to_use": "Use when approval rates or error rates are imbalanced across sensitive groups and you can retrain the model. This is effective when representation differences drive training bias but feature quality is still acceptable. It is a good first intervention before more invasive architecture changes.",
      "tradeoffs": "Reweighting can reduce aggregate AUC if the previous model overfit majority-group patterns. Weight instability may occur for very small subgroups, requiring clipping or regularization. You must monitor calibration drift after retraining.",
      "difficulty": "medium",
      "expected_impact": "Typically improves subgroup recall parity and narrows demographic parity gaps. It may modestly increase false positives in previously under-approved groups. Net fairness impact is usually positive when imbalance stems from training signal skew.",
      "code_snippet": "import numpy as np\nimport pandas as pd\nfrom sklearn.model_selection import train_test_split\nfrom sklearn.ensemble import RandomForestClassifier\n\nfeature_cols = ['income', 'debt_to_income', 'credit_history_years', 'loan_amount']\nX = df[feature_cols]\ny = df['approved']\nA = df['gender']\n\nX_train, X_test, y_train, y_test, A_train, A_test = train_test_split(\n    X, y, A, test_size=0.2, random_state=42, stratify=y\n)\n\n# Inverse-frequency group weights (with clipping for stability)\ngroup_freq = A_train.value_counts(normalize=True)\nweights = A_train.map(lambda g: 1.0 / max(group_freq.get(g, 1e-6), 1e-6))\nweights = np.clip(weights, 0.5, 5.0)\n\nmodel = RandomForestClassifier(n_estimators=300, random_state=42)\nmodel.fit(X_train, y_train, sample_weight=weights)"
    },
    {
      "title": "Post-processing threshold calibration by group",
      "category": "post_processing",
      "when_to_use": "Use when retraining is constrained or when score outputs already exist in production. This is suitable when subgroup disparity appears primarily at a single global threshold. Apply after validating legal/policy constraints for group-conditional decision rules.",
      "tradeoffs": "Operational complexity increases because serving logic must maintain group-specific thresholds and governance controls. Threshold tuning can create precision-recall tradeoffs and may require periodic recalibration. You must document policy rationale and monitor for drift.",
      "difficulty": "medium",
      "expected_impact": "Can quickly reduce approval-rate and false-negative disparities without changing core model weights. Often yields strong short-term parity gains, though long-term fairness still depends on data quality and feature validity. Best results come with continuous subgroup monitoring.",
      "code_snippet": "import numpy as np\nfrom sklearn.metrics import recall_score\n\n# Assume model outputs probability of approval\nproba = model.predict_proba(X_valid)[:, 1]\n\nthresholds = {'female': 0.47, 'male': 0.53}\ndef decision(p, g):\n    return int(p >= thresholds.get(g, 0.5))\n\ny_pred = np.array([decision(p, g) for p, g in zip(proba, df_valid['gender'])])\n\n# Simple subgroup recall monitoring\nfor group in df_valid['gender'].unique():\n    mask = df_valid['gender'] == group\n    print(group, recall_score(y_valid[mask], y_pred[mask]))"
    }
  ]
}

Now produce JSON for:
Task context:
{task_context}

Issue interpretation:
{interpretation}
""".strip()
