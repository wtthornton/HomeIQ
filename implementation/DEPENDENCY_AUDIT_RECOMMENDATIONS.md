# Dependency Audit & Update Recommendations

**Date:** January 2025  
**Status:** 📋 Review Required

## Executive Summary

After reviewing all `package.json` files, I've identified **version mismatches** between frontend projects and several packages that should be updated to latest stable versions. This document provides prioritized recommendations.

---

## 🔴 HIGH PRIORITY - Version Standardization

### Issue: Inconsistent Versions Between Projects

**Problem:** `health-dashboard` and `ai-automation-ui` use different versions of core dependencies, making maintenance difficult and creating potential compatibility issues.

### 1. **ESLint Major Version Mismatch** ⚠️ CRITICAL

| Package | health-dashboard | ai-automation-ui | Recommendation |
|---------|------------------|------------------|----------------|
| `eslint` | `^8.57.0` | `^9.17.0` | **Upgrade health-dashboard to 9.x** |

**Impact:** 
- ESLint 9.x uses flat config (eslint.config.js) vs legacy .eslintrc
- Breaking changes in configuration format
- Different plugin ecosystem compatibility

**Action:** Upgrade health-dashboard to ESLint 9.x and migrate config, OR standardize on ESLint 8.x (not recommended - 8.x is older)

**Recommendation:** ✅ **Upgrade health-dashboard to ESLint 9.17.0** (matches ai-automation-ui)

---

### 2. **TypeScript ESLint Package Mismatch** ⚠️ CRITICAL

| Package | health-dashboard | ai-automation-ui | Issue |
|---------|------------------|------------------|-------|
| TypeScript ESLint | `@typescript-eslint/eslint-plugin: ^7.18.0`<br>`@typescript-eslint/parser: ^7.18.0` | `typescript-eslint: ^8.48.0` | **Different package names!** |

**Problem:** 
- health-dashboard uses old separate packages (`@typescript-eslint/*`)
- ai-automation-ui uses unified package (`typescript-eslint`)
- Version 8.x is unified package, version 7.x is old format

**Action:** ✅ **Upgrade health-dashboard to unified `typescript-eslint@^8.48.0`** and remove old packages

---

### 3. **Vite Major Version Mismatch** ⚠️ HIGH

| Package | health-dashboard | ai-automation-ui | Recommendation |
|---------|------------------|------------------|----------------|
| `vite` | `^5.4.8` | `^6.4.1` | **Upgrade health-dashboard to 6.x** |

**Impact:**
- Vite 6.x has performance improvements and new features
- Breaking changes in plugin system
- Better ESM support

**Action:** ✅ **Upgrade health-dashboard to Vite 6.4.1** (matches ai-automation-ui)

**Dependencies to also update:**
- `@vitejs/plugin-react`: `^4.3.1` → `^4.7.0` (matches ai-automation-ui)
- Check Vitest compatibility (may need Vitest 4.x for Vite 6.x)

---

### 4. **Vitest Major Version Mismatch** ⚠️ HIGH

| Package | health-dashboard | ai-automation-ui | Recommendation |
|---------|------------------|------------------|----------------|
| `vitest` | `^3.2.4` | `^4.0.15` | **Upgrade health-dashboard to 4.x** |

**Impact:**
- Vitest 4.x requires Node.js 18+
- Better performance and TypeScript support
- Breaking changes in config format

**Action:** ✅ **Upgrade health-dashboard to Vitest 4.0.15** (matches ai-automation-ui)

---

### 5. **TypeScript Version Mismatch** ⚠️ MEDIUM

| Package | health-dashboard | ai-automation-ui | Recommendation |
|---------|------------------|------------------|----------------|
| `typescript` | `^5.6.3` | `^5.9.3` | **Upgrade health-dashboard to 5.9.3** |

**Impact:** Patch version updates (bug fixes, minor improvements)

**Action:** ✅ **Upgrade health-dashboard to TypeScript 5.9.3** (matches ai-automation-ui)

---

### 6. **Chart.js Version Mismatch** ⚠️ MEDIUM

| Package | health-dashboard | ai-automation-ui | Recommendation |
|---------|------------------|------------------|----------------|
| `chart.js` | `^4.4.4` | `^4.5.1` | **Upgrade health-dashboard to 4.5.1** |

**Impact:** Minor version update (features, bug fixes)

**Action:** ✅ **Upgrade health-dashboard to chart.js 4.5.1** (matches ai-automation-ui)

---

## 🟡 MEDIUM PRIORITY - Build Tool Updates

### 7. **CSS Build Tools Version Mismatch**

| Package | health-dashboard | ai-automation-ui | Recommendation |
|---------|------------------|------------------|----------------|
| `tailwindcss` | `^3.4.13` | `^3.4.18` | Upgrade to 3.4.18 |
| `postcss` | `^8.4.41` | `^8.4.49` | Upgrade to 8.4.49 |
| `autoprefixer` | `^10.4.20` | `^10.4.22` | Upgrade to 10.4.22 |

**Action:** ✅ **Upgrade health-dashboard CSS tools to match ai-automation-ui**

---

## 🟢 LOW PRIORITY - Testing Library Updates

### 8. **Testing Library Versions** ✅ Already Consistent

Both projects use the same versions:
- `@testing-library/react`: `^16.3.0`
- `@testing-library/jest-dom`: `^6.9.1`
- `@testing-library/user-event`: `^14.6.1`

**Action:** ✅ **No changes needed** - already consistent

---

## 📋 Recommended Change List

### health-dashboard/package.json Updates

```json
{
  "devDependencies": {
    // CRITICAL - ESLint upgrade (requires config migration)
    "eslint": "^9.17.0",  // was: ^8.57.0
    
    // CRITICAL - TypeScript ESLint unified package
    "typescript-eslint": "^8.48.0",  // NEW - unified package
    // REMOVE: "@typescript-eslint/eslint-plugin": "^7.18.0",
    // REMOVE: "@typescript-eslint/parser": "^7.18.0",
    
    // HIGH - Vite major upgrade
    "vite": "^6.4.1",  // was: ^5.4.8
    "@vitejs/plugin-react": "^4.7.0",  // was: ^4.3.1
    
    // HIGH - Vitest major upgrade
    "vitest": "^4.0.15",  // was: ^3.2.4
    "@vitest/ui": "^4.0.15",  // was: ^3.2.4 (check compatibility)
    
    // MEDIUM - TypeScript patch update
    "typescript": "^5.9.3",  // was: ^5.6.3
    
    // MEDIUM - CSS build tools
    "tailwindcss": "^3.4.18",  // was: ^3.4.13
    "postcss": "^8.4.49",  // was: ^8.4.41
    "autoprefixer": "^10.4.22",  // was: ^10.4.20
  },
  "dependencies": {
    // MEDIUM - Chart.js minor update
    "chart.js": "^4.5.1"  // was: ^4.4.4
  }
}
```

---

## ⚠️ Breaking Changes & Migration Notes

### ESLint 8 → 9 Migration

**Required Changes:**
1. Convert `.eslintrc.*` to `eslint.config.js` (flat config)
2. Update plugin imports and configuration format
3. Review and update ESLint rules (some renamed/removed)

**Migration Guide:** https://eslint.org/docs/latest/use/migrate-to-9.0.0

### TypeScript ESLint 7 → 8 Migration

**Required Changes:**
1. Replace `@typescript-eslint/eslint-plugin` and `@typescript-eslint/parser` with unified `typescript-eslint` package
2. Update imports in config
3. Review rule changes in v8

**Migration Guide:** https://typescript-eslint.io/docs/getting-started/

### Vite 5 → 6 Migration

**Required Changes:**
1. Review plugin compatibility
2. Check build output format changes
3. Update any custom Vite config

**Migration Guide:** https://vitejs.dev/guide/migration.html

### Vitest 3 → 4 Migration

**Required Changes:**
1. Update config format (if using legacy format)
2. Check plugin compatibility
3. Review API changes

**Migration Guide:** https://vitest.dev/guide/migration.html

---

## 🔍 Additional Recommendations

### 9. **React Ecosystem** ✅ Already Current

Both projects use React 18.3.1, which is current. React 19 is still in RC/beta (not recommended for production yet).

### 10. **Playwright** ✅ Already Current

- Root: `^1.56.1`
- tests/e2e: `^1.56.1`
- health-dashboard: `^1.56.1`

**Action:** ✅ **No changes needed** - latest stable

### 11. **Puppeteer** ⚠️ REVIEW NEEDED

- Root package.json: `puppeteer: ^24.30.0`

**Question:** Is Puppeteer still being used? If so, consider migrating to Playwright (better maintenance, more features).

**Action:** ⚠️ **Review usage** - if unused, remove. If used, consider Playwright migration.

---

## 📊 Priority Summary

| Priority | Category | Packages | Impact |
|----------|----------|----------|--------|
| 🔴 **CRITICAL** | ESLint & TypeScript ESLint | 2 packages | Breaking changes, config migration required |
| 🟠 **HIGH** | Build Tools (Vite, Vitest) | 3 packages | Major version upgrades, breaking changes |
| 🟡 **MEDIUM** | TypeScript, Chart.js, CSS tools | 4 packages | Patch/minor updates, low risk |
| 🟢 **LOW** | Review/Standardization | 1 package (Puppeteer) | Usage review needed |

---

## 🚀 Recommended Upgrade Sequence

1. **Phase 1: Low-Risk Updates** (Week 1)
   - ✅ TypeScript 5.6.3 → 5.9.3
   - ✅ Chart.js 4.4.4 → 4.5.1
   - ✅ CSS tools (tailwindcss, postcss, autoprefixer)

2. **Phase 2: Build Tools** (Week 2)
   - ⚠️ Vite 5 → 6 (requires testing)
   - ⚠️ Vitest 3 → 4 (requires testing)
   - ⚠️ @vitejs/plugin-react update

3. **Phase 3: ESLint Ecosystem** (Week 3)
   - ⚠️ ESLint 8 → 9 (requires config migration)
   - ⚠️ TypeScript ESLint 7 → 8 (unified package)

4. **Phase 4: Verification** (Week 4)
   - ✅ Run full test suite
   - ✅ Verify builds work
   - ✅ Check for linting errors

---

## ⚡ Quick Wins (Can Do Now)

These are safe to update immediately:

1. **health-dashboard:**
   - `typescript`: `^5.6.3` → `^5.9.3`
   - `chart.js`: `^4.4.4` → `^4.5.1`
   - `tailwindcss`: `^3.4.13` → `^3.4.18`
   - `postcss`: `^8.4.41` → `^8.4.49`
   - `autoprefixer`: `^10.4.20` → `^10.4.22`

**Risk:** LOW - patch/minor updates only

---

## 📝 Notes

1. **Version Standardization:** Priority is to get both frontend projects using the same versions for easier maintenance
2. **Breaking Changes:** ESLint 9, Vite 6, and Vitest 4 all have breaking changes - plan migration carefully
3. **Testing:** After each phase, run full test suite and verify builds
4. **Documentation:** Update any documentation referencing old versions
5. **CI/CD:** Ensure CI/CD pipelines support new versions

---

## ✅ Verification Checklist

After updates, verify:

- [ ] `npm install` completes without errors
- [ ] `npm run build` succeeds for both projects
- [ ] `npm test` passes for both projects
- [ ] `npm run lint` passes for both projects
- [ ] No deprecation warnings in npm output
- [ ] Docker builds succeed
- [ ] No runtime errors in development mode
- [ ] Production builds deploy successfully

---

**Next Steps:**
1. Review this document
2. Approve recommended changes
3. Execute Phase 1 (quick wins) first
4. Plan Phase 2-3 (breaking changes) with testing schedule
5. Update this document with completion status

