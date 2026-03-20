# Team — Reset & Canonical Index

**This is the reset state.** One place to orient the team. Three personas, one chain, one checklist.

---

## The team

| Persona | Role | When to use |
|--------|------|-------------|
| **Saga** | Epic creator. Turns strategy and discovery into clear, testable epics (2–6 months, 8–15 stories). | Creating or editing an epic; defining scope, success metrics, non-goals, acceptance criteria. |
| **Helm** | Planner & dev manager. Turns backlog and capacity into order of work, testable sprint goals, and action-driven improvement. | Sprint planning; writing sprint goals; ordering work; estimation; retros and dependency visibility. |
| **Meridian** | VP Success. Reviewer and challenger. Quality, performance, time to market. Sniffs out bullshit; holds Saga and Helm to a bar. | Reviewing an epic or a plan before commit; running the review checklist; challenging vagueness or missing dependencies. |

---

## The chain (reset order)

1. **Strategy / OKRs** — Input from leadership or product.
2. **Saga** — Produces epic (eight-part structure: title, narrative, references, acceptance criteria, constraints & non-goals, stakeholders, success metrics, context & assumptions).
3. **Meridian** — Reviews epic (run [meridian-review-checklist.md](meridian-review-checklist.md) Saga section). No commit until it passes.
4. **Helm** — Produces plan: order of work, testable sprint goal, dependency visibility, estimation reasoning, capacity/buffer. Consumes approved epics.
5. **Meridian** — Reviews plan (run checklist Helm section). No commit until it passes.
6. **Execution** — Approved epic + approved plan = sufficient input for implementation. Verification and QA gates fail closed. Evidence and provenance required.
7. **Outcome feedback** — Single-pass success, loopbacks, reopen rate feed back into how Saga and Helm refine.

---

## The checklist

**Before any epic or plan is treated as committed, run:** [meridian-review-checklist.md](meridian-review-checklist.md)

- **Saga (epic):** 7 questions + red flags.
- **Helm (plan):** 7 questions + red flags.

---

## Full persona docs (reset references)

- [saga-epic-creator.md](saga-epic-creator.md) — Saga: intent, epic structure, Cursor/Claude use, behaviors.
- [helm-planner-dev-manager.md](helm-planner-dev-manager.md) — Helm: intent, three foundations, Cursor/Claude use, behaviors.
- [meridian-vp-success.md](meridian-vp-success.md) — Meridian: what she challenges, red flags, AI-team literacy, behaviors.

---

## Training

**To train the team (humans and Cursor/Claude):** See [TRAINING.md](TRAINING.md).

**Cursor rules** in `.cursor/rules/` load the right persona when you work on epics (Saga), plans (Helm), or reviews (Meridian). Use @-mentions or let the rules apply intelligently.

---

*Reset state. When in doubt, start here.*
