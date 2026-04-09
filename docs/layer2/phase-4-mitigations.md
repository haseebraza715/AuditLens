# Layer 2 Phase 4: Mitigation Recommendations

## Implemented

- Implemented `recommend_node` for per-issue mitigation generation.
- Supported mitigation output fields:
  - `title`
  - `category`
  - `when_to_use`
  - `tradeoffs`
  - `difficulty`
  - `expected_impact`
  - `code_snippet`
- Added normalization, deduplication, and ranking:
  - category-based priority
  - difficulty-aware ordering
  - title/category dedupe
- Added fallback recommendation sets when provider output is invalid.

## Key Design Decisions

- Every interpreted issue returns at least one mitigation.
- Ranking is deterministic and does not depend on provider ordering.
- Fallback recommendations prioritize practical, low-friction actions.

## Challenges and Solutions

- Challenge: recommendation payloads may be malformed or incomplete.
  - Solution: strict normalization with deterministic fallback generation.
- Challenge: duplicate ideas lower report quality.
  - Solution: dedupe on `(title, category)` before ranking.
