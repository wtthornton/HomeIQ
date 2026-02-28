---
epic: frontend-framework-upgrades
priority: medium
status: open
estimated_duration: 3-4 weeks
risk_level: medium
source: Phase 4 deferral, frontend-redesign-plan.md, Context7 library research
---

# Epic: Frontend Framework Upgrades (React 19, Vite 7, Tailwind 4)

**Status:** Open
**Priority:** Medium (P2)
**Duration:** 3-4 weeks
**Risk Level:** Medium — major version upgrades with breaking changes
**Predecessor:** Epics frontend-security-hardening, health-dashboard-quality, ai-automation-ui-quality (quality fixes first, then upgrade)
**Affects:** health-dashboard, ai-automation-ui

## Context

React 18→19, Vite 6→7, and Tailwind 3→4 were explicitly deferred from the Phase 4b
frontend redesign. These are major version upgrades with breaking changes that should
be done after the quality/security foundation is solid.

Research via Context7 and TAPPS expert consultation identified the key breaking changes
and migration paths. Full research docs in `docs/research/2026-frontend-tech-stack-research.md`.

## Stories

### Story 1: React 19 Migration — Health Dashboard

**Priority:** Medium | **Estimate:** 3 days | **Risk:** Medium

**Key Breaking Changes (React 19):**
- `ref` is now a regular prop (no `forwardRef` needed)
- `useContext` replaced by `use(Context)`
- `Suspense` behavior changes (shows fallback until all siblings ready)
- Removed: `propTypes`, `defaultProps` on function components
- Removed: `ReactDOM.render` (must use `createRoot`)
- `use()` hook for promises and context
- Ref cleanup functions (return cleanup from ref callback)

**Acceptance Criteria:**
- [ ] `react` and `react-dom` upgraded to ^19.0.0
- [ ] `@types/react` and `@types/react-dom` upgraded
- [ ] All `forwardRef` usages migrated to direct ref prop
- [ ] `createRoot` confirmed (already used via Vite)
- [ ] All third-party UI libs verified compatible (Radix UI, Recharts, react-use-websocket)
- [ ] Full test suite passes
- [ ] No React deprecation warnings in console

---

### Story 2: React 19 Migration — AI Automation UI

**Priority:** Medium | **Estimate:** 3 days | **Risk:** Medium

**Additional concerns for AI UI:**
- `react-force-graph` compatibility with React 19 (Three.js dependency chain)
- Framer Motion compatibility
- TanStack Query v5 + React 19 interop
- Zustand React 19 compatibility

**Acceptance Criteria:**
- [ ] Same React 19 migration as Story 1
- [ ] `react-force-graph` tested — if incompatible, replace with compatible alternative or isolate in iframe
- [ ] Framer Motion upgraded to React 19-compatible version
- [ ] TanStack Query confirmed compatible
- [ ] 6 npm vulnerabilities in `react-force-graph` chain reassessed post-upgrade

---

### Story 3: Vite 7 Migration — Both Apps

**Priority:** Medium | **Estimate:** 3 days | **Risk:** Low-Medium

**Key Breaking Changes (Vite 7):**
- Environment API stabilized — `import.meta.env` behavior changes
- Config changes: `ssr.resolve.conditions` → `resolve.conditions`
- Minimum Node.js version likely bumped (verify)
- `css.lightningcss` may become default preprocessor
- Plugin API changes for `resolveId`, `load`, `transform`

**Acceptance Criteria:**
- [ ] Vite upgraded to ^7.0.0 in both apps
- [ ] `vite.config.ts` updated for any deprecated options
- [ ] All `import.meta.env.VITE_*` references verified working
- [ ] Build output sizes compared before/after (no regressions)
- [ ] Dev server HMR working correctly
- [ ] All proxy configurations still functional

---

### Story 4: Tailwind CSS 4 Migration — Both Apps

**Priority:** Low | **Estimate:** 1-2 weeks | **Risk:** Medium

**Key Breaking Changes (Tailwind 4):**
- CSS-first configuration: `tailwind.config.js` → `@theme {}` in CSS
- New `@import "tailwindcss"` replaces `@tailwind base/components/utilities`
- Renamed utilities: `shadow-sm` → `shadow-xs`, `shadow` → `shadow-sm`, etc.
- `bg-opacity-*` removed — use `bg-black/50` syntax instead
- Default border color changed from `gray-200` to `currentColor`
- `ring-*` utilities offset changed to 0 (was 3px)
- `@apply` behavior changes with `!important`
- Automatic content detection (no `content` config needed)

**Acceptance Criteria:**
- [ ] Tailwind upgraded to v4 in both apps
- [ ] `tailwind.config.js` migrated to `@theme {}` CSS blocks
- [ ] All renamed utility classes updated (`shadow-sm` → `shadow-xs`, etc.)
- [ ] `bg-opacity-*` patterns migrated to `/` syntax
- [ ] `design-system.css` updated for new Tailwind 4 patterns
- [ ] Visual regression: screenshot comparison before/after for key pages
- [ ] No layout or styling differences visible

---

### Story 5: Update Node.js & Package Tooling

**Priority:** Low | **Estimate:** 4h | **Risk:** Low

**Problem:** May need Node.js upgrade for Vite 7. Package lockfiles should be audited.

**Acceptance Criteria:**
- [ ] Node.js version in Dockerfiles updated if required by Vite 7
- [ ] `.nvmrc` or `engines` field updated in both `package.json`
- [ ] `package-lock.json` regenerated with `npm ci`
- [ ] `npm audit` clean or all remaining vulns documented with justification
