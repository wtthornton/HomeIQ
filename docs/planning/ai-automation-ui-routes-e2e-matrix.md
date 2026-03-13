# AI Automation UI — Route vs E2E Spec Matrix

**Purpose:** Map each app route to the E2E spec(s) that cover it (Epic 49.12).

**App routes** (from `domains/frontends/ai-automation-ui/src/App.tsx`):

| Route | E2E spec(s) | Notes |
|-------|-------------|--------|
| `/` (Ideas) | `ai-automation-ui/pages/dashboard.spec.ts` | Ideas dashboard, suggestions |
| `/chat` | `ai-automation-ui/pages/ha-agent-chat.spec.ts` | HA Agent Chat |
| `/explore` | `ai-automation-ui/pages/discovery.spec.ts` | Discovery / device explorer |
| `/insights` | `ai-automation-ui/pages/patterns.spec.ts` | Insights / patterns |
| `/automations` | `ai-automation-ui/pages/deployed.spec.ts` | Deployed automations |
| `/scheduled` | `ai-automation-ui/pages/scheduled.spec.ts` | Scheduled AI tasks |
| `/settings` | `ai-automation-ui/pages/settings.spec.ts` | Settings |
| `/name-enhancement` | `ai-automation-ui/pages/name-enhancement.spec.ts` | Name Enhancement dashboard |

**Legacy redirects (resolved to above):**

| Legacy path | Redirects to | Covered by |
|-------------|--------------|------------|
| `/ha-agent` | `/chat` | ha-agent-chat.spec.ts |
| `/deployed` | `/automations` | deployed.spec.ts |
| `/discovery` | `/explore` | discovery.spec.ts |
| `/patterns` | `/insights` | patterns.spec.ts |
| `/synergies` | `/insights` | patterns.spec.ts, synergies.spec.ts |
| `/admin` | `/settings?section=system` | settings.spec.ts, admin.spec.ts |
| `/proactive` | `/?source=context` | dashboard.spec.ts, proactive.spec.ts |
| `/blueprint-suggestions` | `/?source=blueprints` | blueprint-suggestions.spec.ts, dashboard.spec.ts |

**Additional specs (workflows / components):**

- `workflows/ask-ai-mocked.spec.ts` — Ask AI mocked (CI)
- `workflows/ask-ai-complete.spec.ts` (root) — Ask AI full flow (local)
- `workflows/automation-creation.spec.ts`, `conversation-flow.spec.ts`
- `pages/enhancement-button.spec.ts` — Enhance button on Chat (post-creation)
- `pages/navigation.spec.ts` — Sidebar/navigation
- `pages/synergies-filtering-sorting.spec.ts`, `pages/deployed-buttons.spec.ts`

**Coverage gaps addressed in Epic 49:**

- `/name-enhancement`: added `name-enhancement.spec.ts` (navigate + assert main content).
- `/scheduled`: added `scheduled.spec.ts` (navigate + assert main content + console errors).
