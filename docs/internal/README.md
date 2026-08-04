# Internal documentation

> **Archived:** Every document under this directory is retained as historical
> planning context. Dates, layouts, commands, test counts, and roadmap status
> may be stale. Use the root README and CHANGELOG for current guidance.

Planning notes and phase write-ups that lived under `docs/` have been moved here so the top-level **`docs/`** folder stays small and public-facing.

| Path | Contents |
|------|----------|
| `AGENT.md` | Contributor / agent working notes (optional) |
| `bias_audit_mvp_plan.md` | Original MVP plan |
| `main-idea.md` | Product / architecture notes |
| `ui-plan.md` | Streamlit UI planning |
| `layer2/` | Layer 2 phase documents |
| `layer3/` | Layer 3 phase documents |

The former execution roadmap is archived at [`../next-phase-roadmap.md`](../next-phase-roadmap.md).

## Dataset fixture provenance

`tests/fixtures/adult.data` is a 100-row excerpt of the UCI Adult/Census Income
dataset, used only for deterministic smoke tests. Source: UCI Machine Learning
Repository, Adult dataset (Becker & Kohavi, 1996), licensed by UCI under
CC BY 4.0. The committed fixture SHA-256 is
`5b00264637dbfec36bdeaab5676b0b309ff9eb788d63554ca0a249491c86603d`.
Tests must not silently replace or expand this fixture.

## PyPI name check (Phase 1.6)

As of the Phase 1 pass, `python3 -m pip index versions auditlens` reported **no matching distribution**, which indicates the **`auditlens`** project name is **not** published on PyPI yet (suitable for reservation when you publish).
