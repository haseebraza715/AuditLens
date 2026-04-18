"""
Use a custom `BaseLLMClient` with `audit()` so Layer 2 does not require OpenAI/Groq/OpenRouter env vars.

The Layer 2 nodes branch on distinctive substrings in each prompt (same contract as the test
`ScriptedLLMClient` in `tests/interpretation/test_layer2_pipeline.py`).
"""

from __future__ import annotations

import json
import re

import pandas as pd

from auditlens import audit
from auditlens.interpretation.llm.base import BaseLLMClient


class ScriptedDemoLLM(BaseLLMClient):
    """Returns deterministic JSON for the Layer 2 prompt sequence."""

    def complete_json(self, prompt: str) -> str:
        if "Extract structured context" in prompt:
            return json.dumps(
                {
                    "task_type": "binary_classification",
                    "affected_population": "Applicants",
                    "decision_impact": "Eligibility screening",
                    "stakes_level": "high",
                    "confidence": 0.85,
                    "assumptions": [],
                    "needs_clarification": False,
                }
            )

        if "Given task context and one statistical issue" in prompt:
            issue_id_match = re.search(r'"issue_id"\s*:\s*"([^"]+)"', prompt)
            issue_id = issue_id_match.group(1) if issue_id_match else "unknown_issue"
            return json.dumps(
                {
                    "issue_id": issue_id,
                    "why_harmful": "Subgroup performance may diverge under this pattern.",
                    "at_risk_groups": ["group_a"],
                    "likely_model_impact": "May increase error disparity.",
                    "severity_delta": "equal",
                    "severity_rationale": "Task impact aligns with statistical severity.",
                }
            )

        if "ML bias mitigation advisor" in prompt:
            return json.dumps(
                {
                    "mitigations": [
                        {
                            "title": "Apply class-balanced reweighting",
                            "category": "reweighting",
                            "when_to_use": "When subgroup outcomes are imbalanced.",
                            "tradeoffs": "Can shift global optimization behavior.",
                            "difficulty": "medium",
                            "expected_impact": "Improves subgroup parity.",
                            "code_snippet": "model.fit(X_train, y_train, sample_weight=weights)",
                        }
                    ]
                }
            )

        return "{}"


if __name__ == "__main__":
    df = pd.DataFrame({"target": [0] * 80 + [1] * 20, "sex": ["M", "F"] * 50})
    report = audit(
        df,
        target_col="target",
        sensitive_cols=["sex"],
        task_description="Predict loan default for applicants",
        llm_client=ScriptedDemoLLM(),
        layer2_provider="custom",
        layer2_model="scripted-demo",
    )
    assert report.status == "complete"
    print(report.to_markdown()[:800])
