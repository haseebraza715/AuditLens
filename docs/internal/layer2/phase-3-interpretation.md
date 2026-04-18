# Layer 2 Phase 3: Task-Aware Interpretation

## Implemented

- Implemented `interpret_node` for per-issue reasoning:
  - task-specific harm explanation
  - at-risk groups
  - likely model impact
  - task-adjusted severity delta + rationale
- Added strict interpretation prompt template and JSON parsing.
- Added normalization guardrails:
  - non-empty fallback text for missing fields
  - bounded text lengths
  - severity delta normalization (`higher|equal|lower`)

## Key Design Decisions

- Interpretation failures do not break the full pipeline.
- Fallback interpretations preserve schema validity and keep reports complete.
- Post-processing is deterministic, even when model output quality varies.

## Challenges and Solutions

- Challenge: LLM output can omit required keys.
  - Solution: merge with deterministic fallback interpretation and normalize each field.
- Challenge: generic responses reduce usefulness.
  - Solution: include full issue payload + task context in each per-issue prompt.
