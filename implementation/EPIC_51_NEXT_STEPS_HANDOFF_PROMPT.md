# Handoff: Epic 51 Next Steps — E2E Follow-Up

**Context:** Epic 51 (E2E Skipped Tests — Fix or Delete) is **complete**. All conditional `test.skip()` were removed from Playwright E2E specs; health-dashboard + visual run achieved **0 skipped** (209 passed, 16 failed). Your job is to execute the follow-up steps below and update the plan.

**Read first:** **implementation/VISUAL_BASELINE_AND_E2E_ISSUES_PLAN.md** (§1 and Epic 51 paragraph). Optional: **stories/epic-51-e2e-skipped-tests.md** (Completion notes & Next steps).

---

## Critical rule

All Playwright commands **must** be run **from `tests/e2e`** with **`--config=docker-deployment.config.ts`**. Use **`--project=docker-chromium`** for health-dashboard + visual, **`--project=docker-ai-ui-chromium`** for AI UI. Use **`--workers=1`** for stable runs.

**PowerShell:** Use `Set-Location c:\cursor\HomeIQ\tests\e2e` then run `npx playwright test ...` (no `&&`).

---

## Current state (post–Epic 51)

- **Playwright skips:** 0 conditional skips remain in `tests/e2e/**/*.spec.ts`. Epic 51 goal achieved.
- **Health-dashboard + visual (docker-chromium, --workers=1):** 209 passed, 16 failed, 0 skipped.
- **AI UI:** Not re-run after Epic 51; previous run had 0 failed with 6 skipped — after Epic 51 those skips were removed, so the suite will now run more tests (some may fail on assertion).
- **Epic 51:** Marked Complete in stories/OPEN-EPICS-INDEX.md. Plan and index updated.

---

## Your tasks (in priority order)

### 1. Re-run AI UI suite and record results

From **tests/e2e** run:

```powershell
Set-Location c:\cursor\HomeIQ\tests\e2e
npx playwright test ai-automation-ui --config=docker-deployment.config.ts --project=docker-ai-ui-chromium --workers=1
```

- Note **passed / failed / skipped**.
- Confirm **0 skipped** (Epic 51 removed skips; any skip would be a regression).
- Update **implementation/VISUAL_BASELINE_AND_E2E_ISSUES_PLAN.md**:
  - In **§1**, update the "Current Test Run Summary" table: set the AI UI row to the new pass/fail/skip counts and add a note "Post–Epic 51 run (date)."
  - In the "Last run" / Epic 51 paragraph, add one line: "AI UI post–Epic 51: X passed, Y failed, Z skipped."

### 2. Update the plan §1 table with post–Epic 51 numbers

In **implementation/VISUAL_BASELINE_AND_E2E_ISSUES_PLAN.md** §1:

- Ensure the health-dashboard + visual row reflects: **209 passed, 16 failed, 0 skipped** (post–Epic 51 run).
- Ensure the AI UI row reflects the counts from task 1.
- Keep the "Conclusion" and "Last run" text in sync with the table.

### 3. (Optional) Fix or triage the 16 failing health-dashboard tests

If you have time, address the 16 failures from the post–Epic 51 run. Each failure is a **real assertion** (no skips). Suggested fixes:

| Area | Spec | Failures | Suggested fix |
|------|------|----------|----------------|
| **Forms** | health-dashboard/components/forms.spec.ts | 3 | First input on Configuration is `type="number"`; use `input[type="text"], textarea` only, or fill a valid number. Submit button may be disabled until form valid — wait for enabled or use a different flow. |
| **Navigation** | health-dashboard/components/navigation.spec.ts | 1 | Services tab not visible until "Infrastructure" is expanded. In test, expand Infrastructure (click `button:has-text("Infrastructure")`) before asserting Services tab visible. |
| **RAG modal** | health-dashboard/components/rag-details-modal.spec.ts | 2 | "Loading state" and "error state" tests need API mocks (delay/error response). Add `page.route()` mocks for RAG API, or mark with `test.fixme()` until mocks exist. |
| **Filters** | health-dashboard/interactions/filters.spec.ts | 4 | Services tab has **status dropdown**, not a text filter input. Use selectors for the actual UI (e.g. `select[aria-label*="filter" i]`) for dropdown test; for "filter input" tests, either skip when no text input or add a text filter to the app and re-enable. |
| **Energy** | health-dashboard/pages/tabs/energy.spec.ts | 4 | Energy API unavailable in env → no "Energy Monitoring" heading. Accept error state (e.g. "Error: ...") as valid and assert that, or gate tests behind an env flag when Energy API is up. |
| **Events** | health-dashboard/pages/tabs/events.spec.ts | 1 | Test expects error/retry UI when API returns 500; app may not show it. Either mock 500 and ensure app shows retry, or relax assertion to "no crash" when 500. |
| **Services** | health-dashboard/pages/tabs/services.spec.ts | 1 | "Clicking a service opens a details view" — selector for clickable entries (e.g. `button:has-text("Healthy")`) returns 0. Inspect Services tab DOM; use the same selector as modals.spec.ts (e.g. `getByRole('button', { name: 'Details' })` or the card/link that opens details). |

After fixes, re-run health-dashboard + visual and update the plan with new pass/fail/skip.

### 4. (Optional) Document follow-up in backlog

If the 16 failures are not fixed in this session, add a short "Epic 51 follow-up" item to your backlog or to **stories/OPEN-EPICS-INDEX.md** (e.g. "Fix 16 health-dashboard E2E assertion failures (forms, nav, RAG, filters, energy, events, services)") so the next agent knows.

---

## Useful paths

- **Plan:** implementation/VISUAL_BASELINE_AND_E2E_ISSUES_PLAN.md  
- **Epic 51:** stories/epic-51-e2e-skipped-tests.md  
- **Index:** stories/OPEN-EPICS-INDEX.md  
- **E2E root:** tests/e2e (run all Playwright from here)  
- **Health-dashboard app:** domains/core-platform/health-dashboard/src  
- **Config:** tests/e2e/docker-deployment.config.ts  

---

## Handoff prompt (copy for next agent)

You can hand off with:

> **Epic 51 next steps:** Run the AI UI E2E suite from `tests/e2e` with `--config=docker-deployment.config.ts --project=docker-ai-ui-chromium --workers=1`, record pass/fail/skip, and update **implementation/VISUAL_BASELINE_AND_E2E_ISSUES_PLAN.md** §1 with post–Epic 51 counts for both suites. Optionally fix the 16 failing health-dashboard tests per **implementation/EPIC_51_NEXT_STEPS_HANDOFF_PROMPT.md** (forms, navigation, RAG, filters, energy, events, services).
