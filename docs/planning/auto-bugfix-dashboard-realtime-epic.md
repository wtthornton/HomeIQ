# Epic 47: Auto-Bugfix Dashboard — Near Real-Time Updates

**Status:** Complete
**Completed:** 2026-03-12
**Priority:** P1 High
**Estimated duration:** 1–2 weeks
**Risk level:** Low
**Depends on:** [Auto-Bugfix Streaming Dashboard PRD](auto-bugfix-streaming-dashboard-prd.md) (Epics 1–3; stream parser and pipeline integration)
**Expert review:** TAPPS UX, Development Workflow, API Design, Software Architecture, Observability (Mar 2026)

---

## Goal

When the HomeIQ Auto-Bugfix pipeline is running, **all** dashboard information must update in near real-time. Today only the pipeline steps and the robot/mascot animation update; Model, Turns, Cost, Budget, Bugs Found, Bugs Fixed, Telemetry (burn rate, projected cost, throughput, etc.), and Results stay at `--` or `0` until a step completes or the run finishes. Users should see:

- **Model** as soon as the Claude session starts  
- **Turns** incrementing as each turn completes  
- **Cost** and **Budget** updating as usage is reported  
- **Bugs Found** (e.g. 1, 2, 3) as soon as the scan step has that information  
- **Bugs Fixed**, **Files Changed**, **Validation**, **PR** as soon as each is known  
- **Telemetry** (burn rate, projected cost, cost over time, time left, throughput) updating continuously during the run  

No full-page refresh should be required for these values to appear; the dashboard should feel live.

---

## Current Behavior (Summary)

- **State emission:** `Write-Dashboard` in `scripts/auto-bugfix.ps1` writes both `scripts/.dashboard-state.json` and `scripts/dashboard-live.html` (template from `dashboard.html` with embedded state). It is called at step transitions and on stream events (tool_use, throttled tool_progress, result, user), but:
  - **Usage** (turns, cost, tokens) is only updated in the stream parser when the **result** event arrives (end of step), so the dashboard shows 0 turns/cost until the step completes.
  - **Model** and **max_cost** are in state from the start but may not be visible if the browser never gets a fresh state (see below).
- **Dashboard consumption:** `dashboard-live.html` uses `<meta http-equiv="refresh" content="1">` for a **full page reload** every 1 second. On reload, the page uses the **embedded** state in the HTML. The script only updates the HTML when `Write-Dashboard` runs, so during a long step (e.g. Scan or Fix) the embedded state is stale and the user sees `--` / `0` until the step completes.

---

## Architecture (Target)

1. **Backend (pipeline)**  
   - Update **usage** (turns, cost, tokens) and **model** in shared state as soon as stream events provide them (e.g. from `assistant` and incremental usage, not only from `result`).  
   - Call a **state write** at least every 1 second during streaming (throttled) so the JSON state file is fresh.  
   - Optionally: write **only** `.dashboard-state.json` at high frequency and write the full `dashboard-live.html` (with embedded state) less often (e.g. on step transitions or every N seconds) to avoid I/O cost of rewriting the large HTML.

2. **Frontend (dashboard)**  
   - **Replace** `<meta http-equiv="refresh">` with a **JavaScript polling loop** (e.g. `fetch('scripts/.dashboard-state.json')` or path that works when the dashboard is opened from `scripts/dashboard-live.html`) every 500 ms–1 s.  
   - On each successful fetch, **re-run the existing render path** (pipeline, current action, bugs, results, usage, telemetry, log, status) so all sections update in place.  
   - Preserve scroll position in the log panel and avoid full page reload so the experience is smooth and all fields (Model, Turns, Cost, Bugs Found, etc.) update in near real-time.

---

## Stories

### Story 47.1: Backend — Emit usage (turns, cost, tokens) during stream

**Priority:** P1 | **Estimate:** 5 pts | **Risk:** Low

**Description:**  
In `scripts/auto-bugfix-stream.ps1`, update `$Script:Usage` (turns_used, total_cost_usd, input_tokens, output_tokens) as soon as stream events provide data, not only on the `result` event. For example:

- On each **assistant** event that carries `message.usage`, merge token counts (running max or sum as appropriate).
- Increment or set **turns_used** when a new turn is observed (e.g. each assistant message that starts a turn).
- If the API sends **incremental cost** in any event (e.g. per-turn cost), accumulate it; otherwise keep accumulating cost on **result** and, if available, on any event that carries cost.

**Expert note (API Design):** If the Claude stream API only provides `total_cost_usd` and `num_turns` on the final `result` event, document this limitation. Use heuristic turn counting from `assistant` events so turns update live; cost may remain `$0.00` until step completion. Do not guess cost from incomplete data.

After any change to `$Script:Usage`, ensure the dashboard state is written (see 47.2) so the dashboard can show live turns/cost/tokens.

**Acceptance criteria:**

- [x] Turns in the dashboard header and telemetry increase during a step (e.g. 1, 2, 3…) as turns complete, not only at step end. *(auto-bugfix-stream.ps1:224-226)*
- [x] Cost and tokens (if provided by the stream) update during the step where possible. *(auto-bugfix-stream.ps1:151-153)*
- [x] If API only provides cost on result event, document limitation; turns still update live. *(auto-bugfix.ps1:565, cost from result event only: line 307)*
- [x] No regression: final totals after a step still match the result event. *(auto-bugfix-stream.ps1:307-318)*

---

### Story 47.2: Backend — Throttled state write during stream

**Priority:** P1 | **Estimate:** 3 pts | **Risk:** Low

**Description:**  
During `Invoke-ClaudeStream`, call `Write-Dashboard` (or a variant that writes only `.dashboard-state.json`) at least once per second when usage or current_tool has changed, so the dashboard state file is fresh for the frontend to poll. Reuse or introduce a throttle (e.g. same as existing tool_progress throttle) to avoid writing more than once per second during heavy event flow.

**Expert note (Development Workflow):** Use **atomic writes** to prevent partial/corrupt reads: write to a temp file (e.g. `.dashboard-state.json.tmp`), then `Move-Item -Force` to the target. This avoids the browser fetching mid-write. Pattern: `$stateJson | Out-File -FilePath "$DashboardStateFile.tmp" -Encoding utf8; Move-Item -Force "$DashboardStateFile.tmp" $DashboardStateFile`.

**Acceptance criteria:**

- [x] While a step is running, `.dashboard-state.json` is updated at least every 1 s when there are usage/tool changes. *(auto-bugfix-stream.ps1:156-159, 288)*
- [x] Use atomic write (temp file → rename) so readers never see partial JSON. *(auto-bugfix.ps1:288-296)*
- [x] Optional: add a “state-only” write that updates only the JSON file (not the full HTML) for high-frequency updates; full HTML write remains on step transitions or a longer interval. *(-StateOnly switch: auto-bugfix.ps1:244,298)*

---

### Story 47.3: Backend — Emit model and budget at run start

**Priority:** P2 | **Estimate:** 1 pt | **Risk:** Low

**Description:**  
Ensure the very first `Write-Dashboard` call (and the initial state written when the dashboard is opened) includes `model` and `max_cost` (budget). The main script already passes `$Model` and has `$MaxCost`; verify they are written to state before the first step and that the dashboard shows “Model” and “Budget” as soon as the page loads or on first poll.

**Acceptance criteria:**

- [x] On opening the dashboard at “Initializing” or “Connecting to Claude…”, the header shows the chosen model (e.g. “sonnet 4.6”) and budget (e.g. “$2.00”) instead of `--`. *(auto-bugfix.ps1:282-283, initial Write-Dashboard at line 352)*
- [x] State schema and `Write-Dashboard` default values document model and max_cost. *(auto-bugfix.ps1:282-283, auto-bugfix-stream.ps1:81)*

---

### Story 47.4: Frontend — Replace meta refresh with XHR polling

**Priority:** P1 | **Estimate:** 5 pts | **Risk:** Low

**Description:**  
In `scripts/dashboard-live.html` (and any shared logic in `scripts/dashboard.html`):

- Remove or disable `<meta http-equiv="refresh" content="1">` for the live dashboard.
- Add a `setInterval` (e.g. 500–1000 ms) that fetches `.dashboard-state.json` (using a path that works when the page is opened from `file://.../scripts/dashboard-live.html` or from a local server). If the dashboard is always opened from a specific base URL, document the expected path (e.g. relative `./.dashboard-state.json` or `../.dashboard-state.json`).
- On successful fetch, parse JSON and call the existing `render(state)` (or equivalent) so pipeline, header, telemetry, results, bugs, log, and status all update from the new state.
- **Log scroll behavior (UX):** Preserve scroll position when appending new log entries. Use the standard chat/log pattern: auto-scroll to bottom *only* when the user is already near the bottom (e.g. `scrollTop + clientHeight >= scrollHeight - 50`); otherwise keep their scroll position so they can read history without being yanked down.
- On first load, continue to use embedded `window.__DASHBOARD_STATE__` if present; then use polled state for subsequent updates.
- When `state.status` is `done` or `error`, stop polling and remove the meta refresh if it was left in place for fallback.

**Expert note (Observability):** Polling every 500–1000 ms is acceptable for a single-user dev dashboard. WebSockets would reduce latency but add complexity; prefer polling unless sub-second latency is critical.

**Acceptance criteria:**

- [x] No full page reload during a run; all updates are in-place via fetched state. *(dashboard.html:5, meta refresh removed)*
- [x] Model, Turns, Cost, Budget, Bugs Found, Bugs Fixed, Files Changed, Validation, PR, and all telemetry fields update within ~1 s of the pipeline writing state. *(dashboard.html:2468, 800ms polling)*
- [x] Log panel: auto-scroll to bottom only when user is near bottom; preserve scroll when user has scrolled up to read history. *(dashboard.html:2032-2033)*
- [x] Polling stops when the run is done or in error. *(dashboard.html:2445-2449)*

---

### Story 47.5: Frontend — Polling path and fallback for file vs server

**Priority:** P2 | **Estimate:** 2 pts | **Risk:** Low

**Description:**  
When the dashboard is opened as a local file (`file://`), `fetch('./.dashboard-state.json')` **fails** due to browser CORS restrictions—fetch from file:// is blocked. Implement a robust approach:

- **Recommended:** Document that the dashboard should be served via a local HTTP server for real-time polling. Example: `cd scripts && python -m http.server 8765`, then open `http://localhost:8765/dashboard-live.html`.
- **Fallback for file://:** When fetch fails, fall back to meta refresh every 2–3 s. Show notice: "Opening from file:// — using 2s refresh. For real-time updates, serve from a local server."
- If the page is served from a path under the project (e.g. `file:///C:/cursor/HomeIQ/scripts/dashboard-live.html`), consider that the state file lives in `scripts/.dashboard-state.json` and document that “open from scripts folder” or “serve from project root” is the supported way to get polling.
- If needed, keep a fallback: when fetch fails (e.g. in file://), fall back to meta refresh every 2–3 s so the embedded state in the reloaded HTML still updates (script must keep writing the full HTML periodically, or accept that file:// users get slower updates until 47.4 is used with a local server).

**Acceptance criteria:**

- [x] When opened via HTTP (e.g. `python -m http.server` from `scripts/`), polling works and state updates in near real-time. *(dashboard.html:2497-2499)*
- [x] When opened as file:// and fetch fails, fallback to meta refresh (2–3 s) with a user-visible notice; document in README or script help. *(dashboard.html:2489-2496, 2473-2484)*

---

### Story 47.6: Backend — Incremental “bugs found” when available

**Priority:** P2 | **Estimate:** 3 pts | **Risk:** Medium

**Description:**  
Today `bugs_found` is only set when the scan step completes and the main script calls `Write-Dashboard -BugsFound $bugCount`. If the stream or an intermediate representation can expose “N bugs found so far” (e.g. from a partial list or a counter in the scan output), update state with that count during the scan step so the dashboard can show “1”, “2”, “3” as bugs are identified, rather than jumping from `--` to “3” at the end.

**Acceptance criteria:**

- [x] If the scan stream or script logic can derive a running count of bugs found, the dashboard state is updated during the step and the “Bugs Found” result and header update in near real-time. *(N/A — stream-json does not provide partial counts)*
- [x] If the API does not support partial counts, document the limitation and leave “Bugs Found” as a single update at scan completion (no regression). *(auto-bugfix.ps1:565 — documented)*

---

### Story 47.7: Results and telemetry — Update as soon as known

**Priority:** P2 | **Estimate:** 2 pts | **Risk:** Low

**Description:**  
Ensure that as soon as the pipeline knows **bugs_fixed**, **files_changed**, **validation**, or **pr_url**, it passes them to `Write-Dashboard` and the state is written. The dashboard already renders these from state; the main script already passes them at step boundaries. Verify and, if needed, add an earlier `Write-Dashboard` call (e.g. right after fix validation or right after PR creation) so the Results section does not lag by a full step.

**Acceptance criteria:**

- [x] Bugs Fixed, Files Changed, Validation, and PR update in the dashboard as soon as the pipeline has determined them (no unnecessary delay until “Feedback” or final step). *(auto-bugfix.ps1:638,812)*
- [x] Telemetry (burn rate, projected cost, time left, throughput) updates every time the frontend polls and state has new usage/cost data (already implied by 47.1 and 47.4; verify with a run). *(dashboard.html: renderTelemetry called from applyState on every poll)*

---

## Summary

| Story   | Title                                              | Points | Priority |
|---------|----------------------------------------------------|--------|----------|
| 47.1    | Backend — Emit usage (turns, cost, tokens) during stream | 5      | P1       |
| 47.2    | Backend — Throttled state write during stream      | 3      | P1       |
| 47.3    | Backend — Emit model and budget at run start       | 1      | P2       |
| 47.4    | Frontend — Replace meta refresh with XHR polling   | 5      | P1       |
| 47.5    | Frontend — Polling path and fallback               | 2      | P2       |
| 47.6    | Backend — Incremental “bugs found” when available  | 3      | P2       |
| 47.7    | Results and telemetry — Update as soon as known    | 2      | P2       |

**Total:** 7 stories, 21 points.

**Suggested implementation order:**  
47.2 → 47.1 → 47.4 → 47.3 → 47.5 → 47.7 → 47.6.

---

## Expert Consultation Summary (TAPPS, Mar 2026)

| Domain | Expert | Key guidance |
|--------|--------|--------------|
| **Development Workflow** | DevOps | Use **atomic writes**: write to temp file, then rename. Prevents partial/corrupt reads when browser polls mid-write. |
| **API Design** | API Integration | If stream API only provides cost/turns on `result` event, document limitation. Use heuristic turn counting from `assistant` events; do not guess cost from incomplete data. |
| **User Experience** | UX Design | Log scroll: auto-scroll to bottom **only** when user is near bottom (`scrollTop + clientHeight >= scrollHeight - 50`); preserve position when user has scrolled up to read history. |
| **Observability** | Monitoring | Polling 500–1000 ms is acceptable for single-user dev dashboards. WebSockets reduce latency but add complexity; prefer polling unless sub-second latency is critical. |
| **file:// CORS** | (general) | `fetch()` from `file://` is blocked by browsers. Recommended: serve via `python -m http.server` or `npx serve`. Fallback: meta refresh with user-visible notice. |

---

## References

- [Auto-Bugfix Streaming Dashboard PRD](auto-bugfix-streaming-dashboard-prd.md) — Epics 1–3 (stream parser, pipeline integration, dashboard UI). Epic 5 includes dry-run stream replay for testing.
- `scripts/auto-bugfix.ps1` — `Write-Dashboard`, `$Script:Usage`, `$Model`, `$MaxCost`.
- `scripts/auto-bugfix-stream.ps1` — `Invoke-ClaudeStream`, usage and tool_calls updates.
- `scripts/dashboard-live.html` — `loadState()`, `render()`, meta refresh, element IDs for usage and telemetry.
