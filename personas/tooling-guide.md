# Tooling Guide — Cursor & Claude for Personas

Version: 1.0 | Last updated: 2026-03-18

Shared reference for how Saga, Helm, and Meridian use Cursor and Claude. Each persona doc links here instead of repeating this content.

---

## Cursor (2026)

### Agent (Cmd/Ctrl+I)

- Unlimited tool calls; semantic codebase search; file read/edit; terminal; web search; browser for validation.
- Persona outputs (epics, plans, checklists) should live in the repo so Agent finds them via semantic search.
- Agent can summarize scope, blockers, and sprint goals from repo docs and issue bodies.

### Rules (`.cursor/rules/`)

- Three persona rules: `persona-saga.mdc`, `persona-helm.mdc`, `persona-meridian.mdc`.
- Rules encode structure (epic template, sprint goal format, review checklist) and link to full persona docs.
- Set to **Apply Intelligently** (description-based trigger) plus **globs** for file-path triggers (e.g. `**/epics/**`, `**/planning/**`, `**/review*`).

### AGENTS.md

- Map agent roles and include a Personas section showing how Saga, Helm, and Meridian feed the execution plane.
- Nested `AGENTS.md` in subdirectories can scope persona behavior.

### Context injection

- Cursor injects project context (open files, git status, recent errors, workspace rules).
- Persona instructions assume Agent already sees repo structure, existing epics, sprint goals, and dependency notes.

### Other features

- **Checkpoints:** Use when drafting or editing epics, plans, or review docs — undo edits if a revision goes wrong.
- **Browser tool:** For demos or acceptance checks, Agent can use the browser to verify sprint goals against a running app.
- **Export:** Export persona chats as markdown for stakeholder review or for attaching to issues/Confluence.

---

## Claude (2026)

### Extended thinking

- Use for complex epics (many stakeholders, compliance, multi-team dependencies), complex planning (dependency trade-offs, capacity), or deep reviews.
- Claude reasons step-by-step before producing output, improving quality for ambiguous or high-stakes work.

### Artifacts

- Use Artifacts to draft and iterate on epic documents (Saga), sprint goal templates and dependency matrices (Helm), or review reports (Meridian).
- Keeps the working document visible and editable in one place.

### Long context (200K)

- Paste discovery notes, OKRs, stakeholder comments, backlog excerpts, and capacity notes so persona outputs are grounded in real input.

### Structured outputs

- Ask for persona outputs in a consistent format (markdown sections matching the persona's required structure) so they can be dropped into Jira, GitHub issues, or project docs.

---

## MCP Servers

### TappsMCP (tapps-mcp)

Code quality, scoring, security, domain experts, and project memory.

**Key tools for personas:**
- `tapps_consult_expert` — Query built-in or custom domains
- `tapps_research` — Combined expert + docs lookup in one call
- `tapps_memory` — Persist architecture decisions and quality patterns across sessions
- `tapps_validate_changed` — Quality gate on changed files before commit

### Context7

Library documentation lookup via `@upstash/context7-mcp`.

### Playwright

Browser automation for acceptance testing and validation.

---

## Integration

| Persona | Feeds into | Purpose |
|---------|-----------|---------|
| **Saga** | Implementation — epic-level acceptance criteria and constraints become the basis for intent and correctness | Defines what "done" means |
| **Helm** | Execution — order of work, sprint goals, dependencies feed planning and prioritization | Defines what comes first and what fits |
| **Meridian** | Quality gate — review bar ensures only clear, testable work gets committed | Holds the bar |

### Evidence and provenance

- When epics and plans are stored in the repo or linked from issues, Cursor and Claude can reference them during implementation and QA, keeping "definition of done" consistent.
- PRs and evidence comments should reflect intent and plan. No "we'll document it later."

---

*Shared tooling reference for Saga, Helm, and Meridian. See individual persona docs for role-specific behaviors.*
