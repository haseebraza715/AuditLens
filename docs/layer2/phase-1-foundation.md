# Layer 2 Phase 1: Foundations

## Implemented

- Added a new `backend/layer2/` package with:
  - pipeline entrypoint (`agent.py`)
  - state contract (`state.py`)
  - node placeholders (`nodes/`)
  - prompt stubs (`prompts/`)
  - provider abstraction (`llm/`)
- Added Layer 2 schemas:
  - `TaskContext`
  - `IssueInterpretation`
  - `MitigationRecommendation`
  - `Layer2Report`
  - API union response models for `/analyze-task`
- Added new `POST /analyze-task` endpoint (multipart):
  - validates existing CSV + column inputs
  - requires `task_description`
  - accepts optional `clarification_answers` JSON
  - returns `needs_clarification` or `complete`
- Added Layer 2 config contract:
  - `LAYER2_PROVIDER` (`openai`/`groq`)
  - provider-specific key/model/base URL env vars
  - timeout/retry/task length limits
- Added dependencies for LangGraph and provider adapters.

## Key Design Decisions

- Kept `POST /analyze` unchanged for backward compatibility.
- Added a separate `POST /analyze-task` endpoint to isolate Layer 2 behavior.
- Introduced provider abstraction early so node logic is not coupled to a single vendor.
- Kept Phase 1 node behavior minimal and deterministic to validate contracts first.

## Challenges and Solutions

- Challenge: Add new response behavior without breaking Layer 1 clients.
  - Solution: New endpoint with explicit status union (`needs_clarification` vs `complete`).
- Challenge: Enforce provider configuration clearly.
  - Solution: centralized settings parser with explicit runtime errors mapped to API `503`.
