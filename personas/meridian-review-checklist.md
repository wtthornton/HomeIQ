# Meridian Review Checklist

Use this checklist when reviewing **Saga** (epic) or **Helm** (plan) outputs before treating work as committed. Run through it async or in a short review; fix or escalate before commit.

---

## Saga — Epic review

- [ ] **One measurable success metric** — What is it, and how will we read it (instrumentation, dashboard, release gate)?
- [ ] **Top three risks** — Quality, performance, or delivery date; how are we mitigating each?
- [ ] **Non-goals in writing** — What are we explicitly not doing?
- [ ] **External dependencies** — Other teams, vendors, platforms; written or agreed commitment (owner, date)?
- [ ] **Link to goal/OKR** — Why this epic now; what outcome does leadership expect?
- [ ] **Testable acceptance criteria** — Verifiable by human or script (no "user feels good").
- [ ] **AI-ready** — If Cursor/Claude implement from this epic alone, do they have enough to know "done" without guessing?

**Red flags:** Vague success, no test for done, no scope boundaries, missing dependencies, unrealistic scope/time, disconnected from strategy, "the AI will figure it out."

---

## Helm — Plan / sprint review

- [ ] **Testable sprint goal** — Objective + how we'll verify it (not a wish).
- [ ] **Single order of work** — First → second → … and what's explicitly out this sprint.
- [ ] **Dependencies confirmed** — In the plan and owning teams confirmed (visible on board).
- [ ] **Estimation reasoning** — For largest/riskiest items: what changed in the conversation, what's still unknown (on the work item).
- [ ] **Retro actions** — From last time: in this plan or backlog; how we know they're done.
- [ ] **Capacity and buffer** — e.g. 80% commitment / 20% buffer; plan within it.
- [ ] **Async-readable** — Someone (or AI) reading the plan later can understand "done" and what's blocked without being in the room.

**Red flags:** Wish not goal, everything P0, hidden dependencies, estimate without reasoning, retro without action, "the agent will handle it," no capacity/buffer.

---

*Source: Meridian persona — VP Success (reviewer & challenger). Use with Saga and Helm personas.*
