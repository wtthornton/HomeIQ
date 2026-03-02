# Post-Blitz Validation & Next Steps Prompt

**Context:** On Mar 2, 2026, a 12-agent team blitz executed 72 stories across 14 epics (P0-P2) in a single session. 187 files changed, +9,798 / -5,384 lines across 13 commits (fe69c9f1..dce7f049). All changes are on the `master` branch, uncommitted to remote.

---

## Prompt (copy everything below)

```
You are picking up after a major agent-team blitz that executed 72 stories across 14 epics on the HomeIQ project. All changes are committed locally on master (13 commits, 187 files, ~10K lines). Nothing has been pushed yet.

Your job is to validate, fix, and stabilize these changes before they go to production. Work through these phases IN ORDER:

## Phase 1: Build Validation (IMMEDIATE)

### 1a. Frontend builds
Run `npm run build` in both frontend apps to catch TypeScript/import errors from the refactoring:
- `domains/core-platform/health-dashboard/`
- `domains/frontends/ai-automation-ui/`

Fix any build errors — the agent blitz refactored components (Epic 2: AlertsPanel, ThemeContext, lazy loading; Epic 3: HAAgentChat split, ModelSelector extraction, API consolidation, dead file deletion) and these need to compile cleanly.

### 1b. Python tests
Run pytest in each changed backend service directory. Key areas:
- `domains/frontends/observability-dashboard/` — 35 new tests (Epic 4)
- `domains/automation-core/` — 42 test stubs replaced with real tests (Epic 6)
- `domains/pattern-analysis/ai-pattern-service/` — 13 test stubs replaced (Epic 6)
- `libs/homeiq-resilience/tests/` — 7 new test files for shared lib modules (Epics 12-14)
- `libs/homeiq-data/tests/` — 1 new test file (Epic 13)

### 1c. Lint pass
Run `ruff check` across all changed Python files. The agents may have introduced inconsistencies.
Use: `git diff --name-only fe69c9f1..HEAD -- '*.py' | xargs ruff check`

## Phase 2: Security Review (Epic 1 Verification)

Verify the security hardening changes actually work:

1. **CORS (nginx):** Read `domains/frontends/ai-automation-ui/nginx.conf` — verify the origin allowlist map works correctly with `$http_origin`. Ensure it's not accidentally blocking legitimate same-origin requests.

2. **CSP headers:** Both nginx configs should have Content-Security-Policy. Verify `style-src 'unsafe-inline'` is present (required for Tailwind). Verify `connect-src` allows the actual backend URLs (not just 'self').

3. **API keys removed:** Confirm zero hardcoded API keys remain:
   ```
   grep -r "VITE_API_KEY\|homeiq-api-key\|sk-\|Bearer.*[a-zA-Z0-9]{20}" --include="*.ts" --include="*.tsx" domains/frontends/ domains/core-platform/health-dashboard/
   ```

4. **Input validation:** Verify `escapeRegExp()` exists in `haClient.ts`, `serviceName` validation in `api.ts`, and `sanitizeUrl()` in `Dashboard.tsx`.

## Phase 3: Deployment Script Dry-Run (Epic 8)

The 8 new deployment scripts in `scripts/` were written without running. Validate them:
1. Read each script and verify service names match current `docker-compose.yml` and domain compose files
2. Check that `scripts/deployment/common.sh` helper functions are sourced correctly
3. Verify `scripts/pre-deployment-check.sh` health endpoint URLs match actual service ports
4. Ensure all scripts are executable: `chmod +x scripts/*.sh scripts/deployment/*.sh`

## Phase 4: Shared Library Integration (Epics 12-14)

The new shared lib modules need verification:
1. Verify `libs/homeiq-resilience/pyproject.toml` exports the new modules (health_check, app_factory, lifespan, http_client, task_manager, scheduler)
2. Verify `libs/homeiq-data/pyproject.toml` exports new modules (base_settings, openai_client, standard_data_api_client)
3. Check the 5 migrated POC services actually import from the shared libs correctly
4. Run `pip install -e libs/homeiq-resilience/ && pip install -e libs/homeiq-data/` in a test venv to verify installability

## Phase 5: Epic 5 Completion (Frontend Framework Upgrades)

The framework upgrade agent prepared code but didn't update package.json. Complete this:
1. In `domains/core-platform/health-dashboard/`:
   - Update react/react-dom to ^19.0.0
   - Update @types/react and @types/react-dom
   - Run `npm install && npm run build` — fix any React 19 breaking changes
2. In `domains/frontends/ai-automation-ui/`:
   - Same React 19 upgrade
   - Check react-force-graph compatibility
3. For Tailwind: stay on 3.x (4.0 migration is too risky without dedicated testing)
4. Update Vite to latest stable in both apps

## Phase 6: Final Validation

After all fixes:
1. Run `tapps_validate_changed()` across all modified Python files
2. Run both frontend builds one final time
3. Run the full Python test suite
4. Create a single "post-blitz stabilization" commit with all fixes
5. Update `stories/OPEN-EPICS-INDEX.md` if Epic 5 status changes

## Key files to know about

- Epic index: `stories/OPEN-EPICS-INDEX.md` (updated, all epics marked complete)
- Deployment plan: `docs/planning/phase-5-deployment-plan.md`
- New CI workflow: `.github/workflows/quality-gate.yml`
- New CONTRIBUTING guide: `CONTRIBUTING.md`
- New shared lib modules: `libs/homeiq-resilience/src/homeiq_resilience/{health_check,app_factory,lifespan,http_client,task_manager,scheduler}.py`
- New shared lib modules: `libs/homeiq-data/src/homeiq_data/{base_settings,openai_client,standard_data_api_client}.py`
- New deployment scripts: `scripts/{pre-deployment-check,deploy-tier1,deploy-tier2,deploy-tier3,deploy-tiers4-8,deploy-tier9,post-deployment-monitor}.sh`
- New ops docs: `docs/operations/{pre-deployment-checklist,known-issues,deployment-report-template}.md`

## Commit range to validate
All agent work: `fe69c9f1..dce7f049` (13 commits)
```
