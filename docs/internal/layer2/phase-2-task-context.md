# Layer 2 Phase 2: Parse, Analyze, and Clarification Gate

## Implemented

- Implemented deterministic `parse_node`:
  - normalizes Layer 1 issue ordering (`high -> medium -> low`, then `issue_id`)
  - prepares partial task context metadata from dataset info
- Implemented `analyze_node`:
  - provider call for task-context extraction
  - strict JSON parsing with retry-on-invalid-JSON
  - normalization of task context fields and confidence
- Implemented ambiguity rules:
  - unknown `task_type`
  - missing affected population
  - missing decision impact
  - confidence below threshold
- Implemented `clarify_node`:
  - generates up to 2 targeted clarification questions
- Wired conditional branch:
  - `analyze -> clarify -> report` when clarification is needed
  - `analyze -> interpret` when context is sufficiently clear

## Key Design Decisions

- Clarification is explicit and bounded (max 2 questions) to keep API flow simple.
- Clarification answers are merged into extracted task context before ambiguity checks.
- Parse logic remains deterministic to preserve reproducibility.

## Challenges and Solutions

- Challenge: provider responses can include malformed JSON.
  - Solution: retry parsing with bounded attempts and explicit invalid-response errors.
- Challenge: ambiguous tasks can trigger noisy questions.
  - Solution: deterministic question generation based only on missing high-impact context fields.
