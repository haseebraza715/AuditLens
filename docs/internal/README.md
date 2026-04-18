# Internal documentation

Planning notes and phase write-ups that lived under `docs/` have been moved here so the top-level **`docs/`** folder stays small and public-facing.

| Path | Contents |
|------|----------|
| `bias_audit_mvp_plan.md` | Original MVP plan |
| `main-idea.md` | Product / architecture notes |
| `ui-plan.md` | Streamlit UI planning |
| `layer2/` | Layer 2 phase documents |
| `layer3/` | Layer 3 phase documents |

The **execution roadmap** for adoption and distribution remains at [`../next-phase-roadmap.md`](../next-phase-roadmap.md).

## PyPI name check (Phase 1.6)

As of the Phase 1 pass, `python3 -m pip index versions auditlens` reported **no matching distribution**, which indicates the **`auditlens`** project name is **not** published on PyPI yet (suitable for reservation when you publish).
