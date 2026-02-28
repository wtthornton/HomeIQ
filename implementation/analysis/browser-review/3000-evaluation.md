# Port 3000 – AI Performance (Evaluation) Tab

**URL:** `http://localhost:3000/#evaluation`  
**Title:** HomeIQ Dashboard  
**Reviewed:** 2026-02-28

---

## Page summary

- **Purpose:** AI/ML performance metrics (e.g. suggestion quality, pattern accuracy, model metrics) from ai-automation-service, ai-pattern-service, or evaluation endpoints.
- **Key UI:** Charts or cards for accuracy, latency, success rate; may show per-model or per-task metrics.

---

## Issues

| # | Severity | Description |
|---|----------|-------------|
| 1 | Medium | **Availability** – AI services may be optional; if not deployed, show “AI evaluation not configured” rather than generic error. |
| 2 | Low | **Metrics meaning** – Labels (e.g. “Accuracy”, “F1”) should have short help or link to docs so product owners understand them. |

---

## Enhancements

| # | Area | Suggestion |
|---|------|------------|
| 1 | Time range | Allow comparison over time (e.g. last 7 days vs. previous 7 days). |
| 2 | Links | Link to Settings (3001) for confidence threshold and to Ideas/Chat for where AI is used. |
| 3 | Accessibility | Charts have text summary or table fallback. |

---

## Links from this page

- **Nav:** All dashboard tabs.
