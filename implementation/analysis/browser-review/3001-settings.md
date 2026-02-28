# Port 3001 – Settings Page

**URL:** `http://localhost:3001/settings`  
**Title:** Settings - HomeIQ  
**Reviewed:** 2026-02-28

---

## Page summary

- **Purpose:** Configure AI automation preferences.
- **Key UI:** Sections: Analysis Schedule (Enable Daily Analysis checkbox, Run Time 24h), Confidence & Quality (Minimum Confidence Threshold slider 50–95%, Maximum Suggestions Per Run input). More sections may exist below the fold.

---

## Issues

| # | Severity | Description |
|---|----------|-------------|
| 1 | Medium | **Run Time** – Display “03:00 AM”; ensure value is saved and persisted (e.g. to backend or localStorage) and that timezone is clear (user local vs. server). |
| 2 | Medium | **Slider** – “Minimum Confidence Threshold” at 70%; ensure label and value are associated (e.g. aria-valuenow, aria-valuetext) and that change is persisted. |
| 3 | Low | **Maximum Suggestions Per Run** – Numeric input “10”; add min/max/step and validation (e.g. 1–50) to avoid invalid or extreme values. |
| 4 | Low | **Scroll** – Page is scrollable; ensure “Save” or “Apply” is reachable and visible or sticky so users don’t miss saving. |
| 5 | Low | **Name Enhancement** – Route `/name-enhancement` exists but is not linked from Settings; add link if it’s a settings-related feature. |

---

## Enhancements

| # | Area | Suggestion |
|---|------|------------|
| 1 | Persistence | Confirm all settings (schedule, confidence, max suggestions) are saved and show “Saved” or “Unsaved changes” indicator. |
| 2 | Accessibility | Group each section with fieldset/legend or aria-labelledby; slider and time input must be fully keyboard and screen-reader friendly. |
| 3 | Validation | Enforce min/max for numeric inputs; show inline error if out of range. |
| 4 | Help | Short help text or tooltips for “Minimum Confidence” and “Maximum Suggestions” so users understand impact. |
| 5 | API/Backend** | If settings call an API, handle errors (e.g. “Could not save; try again”) and avoid silent failure. |

---

## Links from this page

- **In-app:** Ideas, Chat, Insights, Automations, Settings (current) (bottom nav).
- **Other:** Consider adding link to Name Enhancement (`/name-enhancement`) if it belongs under Configure.

Validate persistence and accessibility for all form fields.
