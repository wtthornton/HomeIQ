# Auto-Bugfix Streaming Dashboard — PRD

**Goal:** Replace the blocking `claude --print` calls with `claude --print --output-format stream-json` to provide real-time visibility into what Claude is doing during each pipeline step.

**Current State:** The dashboard shows "Initializing..." for 3-5+ minutes during the Scan and Fix steps because `claude --print` is a blocking call that only returns when complete. No progress is visible.

**Target State:** The dashboard updates in real-time as Claude reads files, calls TappsMCP tools, and generates fixes. Users see which file is being scanned, which tool is running, and partial results as they emerge.

---

## Architecture

### Stream Event Types (from `claude --output-format stream-json`)

| Event Type | Key Fields | Dashboard Use |
|---|---|---|
| `system` (init) | session_id, tools | "Session started" |
| `assistant` | message.content[].type=tool_use, name, input | "Calling tapps_security_scan on data-api/main.py" |
| `tool_progress` | tool_name, elapsed_time_seconds | "Bash running... (3s)" |
| `user` (tool result) | tool_use_result | "tapps_quick_check scored 72/100" |
| `result` | result, total_cost_usd, num_turns, duration_ms | Final output + stats |

### Data Flow (New)

```
$prompt | claude --print --output-format stream-json
    ↓ (line-by-line JSON events)
Stream Parser (ForEach-Object in PS1)
    ├→ assistant + tool_use → Add-LogEntry + Write-Dashboard
    ├→ tool_progress → Update "tool running" indicator
    ├→ result → Capture final output, update dashboard "done"
    └→ All events → Accumulate full output for JSON extraction
```

### Key Constraint
The dashboard uses file-based state (`.dashboard-state.json` → embedded in `dashboard-live.html`). Browser polls every 2 seconds via `<meta http-equiv="refresh">`. Streaming events update the state file frequently so each browser refresh sees fresh data.

---

## Epic 1: Stream Parser Infrastructure (Foundation)

Build the core PowerShell function that wraps `claude --print --output-format stream-json` and processes events line-by-line, updating the dashboard in real-time.

### Story 1.1: Create `Invoke-ClaudeStream` function
**Points:** 5
**Description:** Create a reusable PowerShell function `Invoke-ClaudeStream` that:
- Accepts prompt (via pipeline), max-turns, mcp-config, allowedTools, and a step number
- Runs `claude --print --output-format stream-json` and processes output line-by-line
- Parses each JSON line with `ConvertFrom-Json`
- Routes events by type to handler functions
- Returns the final `result` event's `.result` field as the function output
- Handles errors gracefully (malformed JSON lines, missing fields)

**Acceptance Criteria:**
- [ ] Function defined in `scripts/auto-bugfix-stream.ps1` (dot-sourced by main script)
- [ ] Accepts pipeline input for the prompt
- [ ] Returns the final text result for downstream parsing
- [ ] Does not break if a JSON line is malformed (skip + warn)

### Story 1.2: Handle `assistant` events with tool_use blocks
**Points:** 3
**Description:** When an `assistant` event arrives with `message.content` containing `tool_use` blocks:
- Extract tool name and key input parameters
- Format a human-readable log message (e.g., "Calling tapps_security_scan on libs/homeiq-data/...")
- Call `Add-LogEntry` with the message
- Call `Write-Dashboard` to update the dashboard state

**Acceptance Criteria:**
- [ ] Tool name extracted from `content.name`
- [ ] Key input parameter extracted (file_path for score/scan, question for expert)
- [ ] Truncate long paths to last 2 segments for readability
- [ ] Log entry added and dashboard state written

### Story 1.3: Handle `tool_progress` events
**Points:** 2
**Description:** When a `tool_progress` event arrives:
- Update the dashboard status message with "Running {tool_name}... ({elapsed}s)"
- Write dashboard state so the browser sees the update on next refresh
- Throttle writes to max 1 per second to avoid I/O thrashing

**Acceptance Criteria:**
- [ ] Status message updates with tool name and elapsed seconds
- [ ] Dashboard state written at most once per second
- [ ] No performance impact on the stream processing loop

### Story 1.4: Handle `result` event and capture output
**Points:** 3
**Description:** When the `result` event arrives:
- Capture the `.result` field as the final text output
- Log the completion with turn count, duration, and cost
- Update dashboard with completion stats
- Return the result text for the caller to parse (e.g., JSON extraction)

**Acceptance Criteria:**
- [ ] Final result text captured and returned from function
- [ ] Log entry: "Scan complete: {num_turns} turns, {duration}s, ${cost}"
- [ ] Dashboard updated with step completion
- [ ] Error results (`is_error: true`) logged as errors

### Story 1.5: Handle `assistant` text blocks for progress hints
**Points:** 2
**Description:** When an `assistant` event has `text` content blocks (Claude's reasoning):
- Scan for progress keywords: "scanning", "reading", "found", "checking"
- Extract short progress snippets (first 80 chars of relevant text)
- Add as info-level log entries (throttled to max 1 per 5 seconds to avoid noise)

**Acceptance Criteria:**
- [ ] Text content scanned for progress keywords
- [ ] Short snippets logged as info entries
- [ ] Throttled to avoid flooding the log

---

## Epic 2: Integrate Stream Parser into Pipeline Steps

Replace all 5 `claude --print` calls in `auto-bugfix.ps1` with `Invoke-ClaudeStream`, wiring each step's events to the dashboard.

### Story 2.1: Convert Step 2 (Scan) to streaming
**Points:** 3
**Description:** Replace the blocking scan call:
```powershell
# Before:
$rawOutput = ($findPrompt | claude --print ...) -join "`n"
# After:
$rawOutput = $findPrompt | Invoke-ClaudeStream -Step 2 -MaxTurns 8 -McpConfig $mcpConfig -AllowedTools "..."
```
The scan step is the most important because it's the longest-running and most opaque.

**Acceptance Criteria:**
- [ ] Scan uses `Invoke-ClaudeStream` instead of `claude --print`
- [ ] Dashboard shows real-time tool calls during scan
- [ ] JSON extraction still works on the returned output
- [ ] Scan completes successfully end-to-end

### Story 2.2: Convert Step 3 (Fix) to streaming
**Points:** 3
**Description:** Replace the fix step's `claude --print` call with `Invoke-ClaudeStream`. This step is even longer (25 max turns) and includes file edits.

**Acceptance Criteria:**
- [ ] Fix uses `Invoke-ClaudeStream`
- [ ] Dashboard shows which files are being read/edited
- [ ] Dashboard shows TappsMCP validation calls
- [ ] Fix completes successfully, files are modified

### Story 2.3: Convert Step 4/5 (Chain: Refactor + Test) to streaming
**Points:** 2
**Description:** Convert the optional chain mode steps (refactor and test generation) to streaming.

**Acceptance Criteria:**
- [ ] Both chain steps use `Invoke-ClaudeStream`
- [ ] Dashboard shows refactoring and test generation progress
- [ ] Chain mode still works correctly end-to-end

### Story 2.4: Convert Step 5/7 (Feedback) to streaming
**Points:** 1
**Description:** Convert the feedback collection step to streaming. This is low priority since it's fast, but consistency matters.

**Acceptance Criteria:**
- [ ] Feedback step uses `Invoke-ClaudeStream`
- [ ] Dashboard shows feedback tool calls

---

## Epic 3: Enhanced Dashboard UI for Streaming

Update the dashboard HTML/JS to better display the real-time streaming data.

### Story 3.1: Add "Current Action" panel to dashboard
**Points:** 3
**Description:** Add a new panel between the pipeline steps and the bug table showing:
- Current tool being called (large text, e.g., "tapps_security_scan")
- Target file/path (monospace, truncated)
- Elapsed time for current tool call (JS timer, updates every second)
- Pulsing animation when a tool is running

**Acceptance Criteria:**
- [ ] New panel visible in dashboard layout
- [ ] Shows tool name and target when a tool is running
- [ ] Shows "Waiting for Claude..." between tool calls
- [ ] Elapsed timer ticks in JS (not just on refresh)

### Story 3.2: Add tool call timeline to dashboard
**Points:** 5
**Description:** Add a visual timeline below the current action panel showing all tool calls made so far:
- Each tool call as a horizontal bar with: tool name, target, duration, status
- Color-coded: teal=running, green=complete, red=error
- Bars grow in real-time as the tool runs
- Scrollable if many tool calls

State shape addition:
```javascript
tool_calls: [{
  tool_name: string,
  target: string,      // file path or key arg
  started_at: string,  // ISO timestamp
  duration_s: number,  // elapsed seconds
  status: "running"|"complete"|"error"
}]
```

**Acceptance Criteria:**
- [ ] Timeline renders all tool calls chronologically
- [ ] Running tools show animated bar
- [ ] Completed tools show duration
- [ ] Scrollable container for long sessions

### Story 3.3: Add cost and token tracker to dashboard header
**Points:** 2
**Description:** Add real-time cost and token usage to the dashboard header:
- Input tokens / Output tokens (from assistant event usage)
- Estimated cost in USD (from result event or calculated)
- Turns used / max turns

State shape addition:
```javascript
usage: {
  input_tokens: number,
  output_tokens: number,
  total_cost_usd: number,
  turns_used: number,
  max_turns: number
}
```

**Acceptance Criteria:**
- [ ] Token counts shown in header
- [ ] Cost displayed after result event
- [ ] Turn counter shows progress toward max

### Story 3.4: Replace meta-refresh with smarter polling
**Points:** 3
**Description:** Replace the `<meta http-equiv="refresh" content="2">` full-page reload with JavaScript `setInterval` fetch that:
- Fetches `.dashboard-state.json` every 1 second via XHR
- Only updates changed DOM elements (no full page reload)
- Preserves scroll position in log panel
- Falls back to embedded state on first load
- Stops polling when status is "done" or "error"

**Acceptance Criteria:**
- [ ] No full page reload during operation
- [ ] DOM updated incrementally
- [ ] Scroll position preserved
- [ ] Polling stops on completion

### Story 3.5: Add file diff preview for fix step
**Points:** 3
**Description:** During the Fix step (Step 3), when Claude makes an Edit tool call, extract the old/new strings from the tool input and display a mini diff view in the dashboard.

State shape addition:
```javascript
recent_edits: [{
  file: string,
  old_text: string,    // first 200 chars
  new_text: string,    // first 200 chars
  timestamp: string
}]
```

**Acceptance Criteria:**
- [ ] Edit tool calls captured with old/new text snippets
- [ ] Diff displayed with red/green highlighting
- [ ] Limited to most recent 5 edits
- [ ] Truncated for readability

---

## Epic 4: Streaming Support for Bash Script

Port the streaming changes to `auto-bugfix.sh` for Linux/macOS/WSL users.

### Story 4.1: Create bash stream parser function
**Points:** 5
**Description:** Create a bash function `claude_stream()` that:
- Pipes prompt to `claude --print --output-format stream-json`
- Reads line-by-line with `while IFS= read -r line`
- Parses JSON events using `python3 -c` or `jq`
- Updates dashboard state via `write_dashboard()`
- Returns the final result text

**Acceptance Criteria:**
- [ ] Function works with bash 4+ and requires only python3 or jq
- [ ] Events parsed and logged in real-time
- [ ] Dashboard updated on tool_use events
- [ ] Final result text returned for JSON extraction

### Story 4.2: Convert all bash `claude --print` calls to streaming
**Points:** 3
**Description:** Replace all 5 `claude --print` calls in `auto-bugfix.sh` with `claude_stream()`.

**Acceptance Criteria:**
- [ ] All 5 calls converted
- [ ] Bash script works end-to-end with streaming
- [ ] Dashboard shows real-time progress on Linux/macOS

### Story 4.3: Shared dashboard state schema validation
**Points:** 2
**Description:** Create a shared JSON schema for the dashboard state that both PS1 and bash scripts validate against. Add new fields for streaming data (tool_calls, usage, recent_edits).

**Acceptance Criteria:**
- [ ] Schema file: `scripts/dashboard-state-schema.json`
- [ ] Both PS1 and bash Write-Dashboard functions emit all required fields
- [ ] New streaming fields have sensible defaults (empty arrays, nulls)

---

## Epic 5: Testing and Reliability

### Story 5.1: Add dry-run mode for stream parser
**Points:** 2
**Description:** Add a `--dry-run-stream` flag that replays a saved stream-json file instead of calling Claude. This enables testing the parser and dashboard without API costs.

**Acceptance Criteria:**
- [ ] `--dry-run-stream <file>` flag on both PS1 and bash scripts
- [ ] Reads saved stream file line-by-line with realistic timing
- [ ] Dashboard updates as if a real scan is running
- [ ] Sample stream file saved in `scripts/test-data/sample-stream.jsonl`

### Story 5.2: Error resilience for stream parsing
**Points:** 3
**Description:** Handle edge cases in stream parsing:
- Malformed JSON lines (skip + warn)
- Empty lines between events
- Partial lines (buffer until newline)
- Stream interruption (claude crash mid-stream)
- Rate limit events (log warning, continue)

**Acceptance Criteria:**
- [ ] All edge cases handled without crashing the pipeline
- [ ] Errors logged to activity log
- [ ] Pipeline falls back to capturing whatever output was received

### Story 5.3: Record stream for replay and debugging
**Points:** 2
**Description:** Save the raw stream-json output to a timestamped file in `scripts/.stream-logs/` for post-run debugging and replay testing.

**Acceptance Criteria:**
- [ ] Stream saved to `scripts/.stream-logs/{branch}-{step}.jsonl`
- [ ] Directory gitignored
- [ ] Cleanup: delete logs older than 7 days on startup
- [ ] Can be replayed with `--dry-run-stream`

---

## Summary

| Epic | Stories | Total Points | Priority |
|---|---|---|---|
| E1: Stream Parser Infrastructure | 5 | 15 | P0 — Foundation |
| E2: Integrate into Pipeline Steps | 4 | 9 | P0 — Core |
| E3: Enhanced Dashboard UI | 5 | 16 | P1 — UX |
| E4: Bash Script Parity | 3 | 10 | P2 — Platform |
| E5: Testing and Reliability | 3 | 7 | P1 — Quality |

**Total: 5 Epics, 20 Stories, 57 Points**

### Implementation Order
1. E1 (Stories 1.1-1.4) → E2 (Story 2.1) → Test scan step end-to-end
2. E3 (Stories 3.1, 3.4) → Visual feedback working
3. E2 (Stories 2.2-2.4) → All steps streaming
4. E3 (Stories 3.2, 3.3, 3.5) → Full dashboard polish
5. E5 → Reliability hardening
6. E4 → Bash parity
