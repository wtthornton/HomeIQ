# Port 3000 – Configuration Tab

**URL:** `http://localhost:3000/#configuration`  
**Title:** HomeIQ Dashboard  
**Reviewed:** 2026-02-28

---

## Page summary

- **Purpose:** View or manage configuration (e.g. env, feature flags, API base URLs). May include read-only display of non-sensitive config.
- **Key UI:** Sections for different config areas; possibly links to docs or edit flows (if any).

---

## Issues

| # | Severity | Description |
|---|----------|-------------|
| 1 | **High** | **Secrets** – Ensure no API keys, passwords, or tokens are rendered; mask or omit sensitive keys. |
| 2 | Medium | **Stale config** – If config is cached, show “As of &lt;time&gt;” or refresh button so users know if they’re viewing current state. |
| 3 | Low | **Validation** – If any config is editable from UI, validate and show errors; avoid silent save failures. |

---

## Enhancements

| # | Area | Suggestion |
|---|------|------------|
| 1 | Security | Audit all displayed keys; use “••••••” or “Set” for secrets; link to secure credential store if applicable. |
| 2 | UX | Group by domain (e.g. API, Feature flags, URLs); copy-to-clipboard for non-secret values. |

---

## Links from this page

- **Nav:** All dashboard tabs.
