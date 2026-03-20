# Train Your Team — Saga, Helm, Meridian

How to use the three personas so the team (humans + Cursor + Claude) works in one consistent way. **Reset state:** [TEAM.md](TEAM.md).

---

## 1. Who does what (reminder)

- **Saga** — Creates and refines epics. Output: clear, testable epic (eight-part structure). Never hand off an epic without Meridian review.
- **Helm** — Creates and refines plans and sprint goals. Output: order of work, testable sprint goal, dependencies visible, estimation reasoning. Never commit a plan without Meridian review.
- **Meridian** — Reviews and challenges. Does not write epics or run sprints. Runs the checklist; asks the seven questions for Saga and seven for Helm; calls out red flags.

---

## 2. When to use which persona

| You are… | Use this persona | How (Cursor) | How (Claude) |
|----------|------------------|--------------|--------------|
| Drafting or editing an **epic** (scope, acceptance criteria, success metrics, non-goals) | **Saga** | @persona-saga or open `personas/saga-epic-creator.md`; rule may auto-apply when you work in epic-related files or say "epic" | Paste Saga persona summary + epic structure; ask for epic draft or revision; use Artifacts for the doc |
| Planning a **sprint**, writing **sprint goal**, ordering backlog, doing **estimation** or **dependency review** | **Helm** | @persona-helm or open `personas/helm-planner-dev-manager.md`; rule may auto-apply for planning docs | Paste Helm persona summary; ask for sprint goal or plan; use Artifacts for plan / dependency matrix |
| **Reviewing** an epic or plan before commit, or challenging vagueness / missing deps | **Meridian** | @persona-meridian or open `meridian-review-checklist.md`; run checklist line by line | Paste Meridian persona + checklist; ask for VP-style review; get back gaps and "questions she would ask" |

---

## 3. Training Cursor (Agent)

### Rules in `.cursor/rules/`

Three rules train the Agent to apply the right persona:

- **persona-saga.mdc** — Applied when the user is creating or editing epics, acceptance criteria, or scope. Tells Agent to follow Saga's epic structure and intent; references the full persona doc.
- **persona-helm.mdc** — Applied when the user is planning sprints, writing sprint goals, or working on backlog/order of work. Tells Agent to follow Helm's three foundations and testable goal format; references the full persona doc.
- **persona-meridian.mdc** — Applied when the user is reviewing an epic or plan, or asks for a "Meridian review" or "VP review." Tells Agent to run the checklist and ask Meridian's seven questions; references the checklist and persona doc.

### How to invoke in chat

- **Explicit:** Type e.g. "As Saga, draft an epic for …" or "Run a Meridian review on this epic" or "@persona-saga".
- **Implicit:** When you work in a file or doc that looks like an epic (e.g. `docs/epics/`) or a plan (e.g. `docs/planning/sprint-goal.md`), the rule description may trigger the right persona (Apply Intelligently).
- **Checklist:** Say "Run the Meridian checklist on this [epic|plan]" and the Agent should load the checklist and go through each item.

### What "trained" looks like

- When drafting an epic, Agent suggests or enforces the eight-part structure (title, narrative, references, acceptance criteria, constraints & non-goals, stakeholders, success metrics, context).
- When drafting a sprint goal, Agent uses the template: objective + how we'll verify it (not a wish).
- When reviewing, Agent runs the seven questions and lists red flags instead of rubber-stamping.

---

## 4. Training Claude (standalone or Artifacts)

- **Saga:** Paste the "Intent" and "Epic structure" sections from saga-epic-creator.md (or the full doc). Ask: "Draft an epic for [X] using this structure." Iterate in an Artifact.
- **Helm:** Paste the "Intent" and "Three foundations" / "Testable sprint goals" from helm-planner-dev-manager.md. Ask: "Write a testable sprint goal for [X]" or "Propose an order of work for this backlog."
- **Meridian:** Paste the "Questions she always asks" and "Red flags" from meridian-vp-success.md, or the full meridian-review-checklist.md. Ask: "Review this epic/plan as Meridian and list gaps and the questions you'd ask."

Use **extended thinking** for complex epics or plans (many dependencies, compliance, multi-team). Use **Artifacts** to keep the epic or plan in one place and editable.

---

## 5. Running a Meridian review (everyone)

1. **Before** treating an epic or plan as committed, open [meridian-review-checklist.md](meridian-review-checklist.md).
2. **For an epic:** Go through the Saga section. For each checkbox, answer: do we have it? If not, fix or escalate. Check red flags.
3. **For a plan/sprint:** Go through the Helm section. Same: answer each item; fix or escalate; check red flags.
4. **In Cursor:** You can say "Run the Meridian checklist on this [epic|plan]" and the Agent (with persona-meridian rule) should walk through the checklist and report pass/fail and gaps.
5. **No shortcut:** Don't commit without running the checklist. Meridian's job is to make that non-negotiable.

---

## 6. Chain discipline (keeping the reset)

- **Epics** come from Saga and are reviewed by Meridian before Helm consumes them. Helm doesn't plan from an unapproved epic.
- **Plans** come from Helm and are reviewed by Meridian before execution. Execution follows the approved epic and plan.
- **Outcome data** (single-pass success, loopbacks, reopen rate) should be visible and feed back: did our epic success metric move? Did our sprint goal get verified? Use that to refine the next epic and plan.

---

## 7. Quick reference

- **Reset / start here:** [TEAM.md](TEAM.md)
- **Full personas:** [saga-epic-creator.md](saga-epic-creator.md) | [helm-planner-dev-manager.md](helm-planner-dev-manager.md) | [meridian-vp-success.md](meridian-vp-success.md)
- **Checklist:** [meridian-review-checklist.md](meridian-review-checklist.md)
- **Cursor rules:** `.cursor/rules/persona-saga.mdc`, `persona-helm.mdc`, `persona-meridian.mdc` (reference these personas and checklist)

---

*Train the team once. Use the chain every time. Run the checklist every time.*
