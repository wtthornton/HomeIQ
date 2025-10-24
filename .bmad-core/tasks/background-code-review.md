<!-- Powered by BMAD™ Core -->

# background-code-review

Run AI code reviews continuously in the background during development sessions. Provides real-time quality feedback without interrupting developer flow.

## Purpose

Enable parallel code review during long agent builds by monitoring file changes and running reviews asynchronously. Developer gets notified of issues but continues working.

## Architecture

```
Developer Flow          Background Reviewer
─────────────────      ────────────────────
Write code             Watch for changes
Run tests              │
Mark task [x]    ──────> Detect file save
│                       Run AI review
│                       Cache results
│                       │
Check status     <────── Notify if HIGH severity
│
Continue work           Continue monitoring
```

## When to Use

**Auto-start scenarios:**
- Dev agent starts `*develop-story`
- Story has >5 tasks (long build expected)
- Configuration `qa.background_review.enabled: true`

**Manual trigger:**
- `*start-background-review` - Start background reviewer
- `*check-review-status` - Get current findings
- `*stop-background-review` - Stop background reviewer

## Implementation

### 1. File Watcher

Monitor working directory for changes:

```python
# Background process
import asyncio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class CodeReviewHandler(FileSystemEventHandler):
    def __init__(self, review_queue):
        self.review_queue = review_queue
        self.debounce_timer = {}

    def on_modified(self, event):
        if event.src_path.endswith(('.py', '.ts', '.tsx', '.js')):
            # Debounce: Wait 5s after last change
            self.schedule_review(event.src_path)

    async def schedule_review(self, file_path):
        # Cancel existing timer
        if file_path in self.debounce_timer:
            self.debounce_timer[file_path].cancel()

        # Schedule new review
        timer = asyncio.create_task(
            self.debounced_review(file_path, delay=5.0)
        )
        self.debounce_timer[file_path] = timer

    async def debounced_review(self, file_path, delay):
        await asyncio.sleep(delay)
        await self.review_queue.put(file_path)
```

### 2. Review Queue Processor

```python
class BackgroundReviewer:
    def __init__(self, story_context):
        self.story_id = story_context['story_id']
        self.claude_md = self.load_performance_guide()
        self.coding_standards = self.load_standards()
        self.review_cache = {}

    async def process_queue(self, review_queue):
        while True:
            file_path = await review_queue.get()

            # Skip if recently reviewed (cache hit)
            cache_key = self.get_file_hash(file_path)
            if cache_key in self.review_cache:
                continue

            # Run AI review
            findings = await self.review_file(file_path)

            # Cache results
            self.review_cache[cache_key] = findings

            # Notify if critical
            if any(f['severity'] == 'high' for f in findings):
                self.notify_developer(file_path, findings)

            # Save to progressive log
            await self.save_findings(file_path, findings)

    async def review_file(self, file_path):
        """
        Call Claude API with focused review prompt
        """
        diff = self.get_file_diff(file_path)

        prompt = f"""
        Review this code change in context of HomeIQ project.

        FILE: {file_path}
        STORY: {self.story_id}

        PERFORMANCE REQUIREMENTS (CLAUDE.md):
        {self.get_relevant_performance_requirements(file_path)}

        CODING STANDARDS:
        {self.get_relevant_standards(file_path)}

        DIFF:
        {diff}

        Focus on:
        1. Security vulnerabilities
        2. Performance anti-patterns (blocking async, N+1 queries, memory leaks)
        3. Missing error handling
        4. Test coverage gaps

        Return JSON:
        {{
          "findings": [
            {{"severity": "high|medium|low", "category": "security|performance|quality|testing", "line": 123, "finding": "...", "fix": "..."}}
          ]
        }}
        """

        response = await self.call_claude_api(prompt)
        return response['findings']

    def notify_developer(self, file_path, findings):
        """
        Non-blocking notification to dev agent
        """
        high_severity = [f for f in findings if f['severity'] == 'high']

        notification = f"""
        ⚠️  BACKGROUND REVIEW ALERT ⚠️

        File: {file_path}
        High Severity Issues: {len(high_severity)}

        {self.format_findings(high_severity)}

        Full results: docs/qa/background/{self.story_id}-{timestamp}.yml

        Continue working - these will be reviewed at next task checkpoint.
        """

        # Write to debug log for dev agent to see
        self.append_to_debug_log(notification)
```

### 3. Integration with Dev Agent

**Dev agent modifications:**

```yaml
# During *develop-story

on_start:
  - Start background reviewer if enabled
  - Show: "Background review active - you'll be notified of critical issues"

during_development:
  - Dev writes code normally
  - Background reviewer runs in parallel
  - High severity findings → appear in debug log
  - Dev can check status: *check-review-status

at_task_completion:
  - Check background review cache for this task's files
  - Surface all findings (not just HIGH)
  - Apply progressive review decision logic
  - Clear cache for reviewed files

on_story_complete:
  - Stop background reviewer
  - Consolidate all background findings
  - Feed into final QA review
```

## Output Format

### Background Review Log

```yaml
# docs/qa/background/1.3-20250124-103045.yml

background_review:
  story_id: "1.3"
  session_start: "2025-01-24T10:30:00Z"
  session_end: "2025-01-24T14:15:00Z"
  files_reviewed: 12
  total_findings: 8

findings:
  - timestamp: "2025-01-24T10:35:12Z"
    file: "services/auth-api/src/login.py"
    trigger: "file_modified"
    severity: high
    category: security
    line: 45
    finding: "No rate limiting on login endpoint"
    fix: "Add @rate_limit(max_requests=5, window=60)"
    status: "notified"  # notified|deferred|fixed

  - timestamp: "2025-01-24T11:02:33Z"
    file: "services/auth-api/src/middleware.py"
    trigger: "file_created"
    severity: medium
    category: performance
    line: 23
    finding: "Synchronous HTTP call blocks event loop"
    fix: "Use aiohttp.ClientSession instead of requests"
    status: "deferred"

summary:
  high_severity: 2
  medium_severity: 4
  low_severity: 2
  developer_notified: 2
  fixed_during_session: 0
  deferred_to_qa: 8
```

### Developer Status Check

```bash
$ *check-review-status

Background Review Status:
─────────────────────────
⏱️  Session Duration: 2h 15min
📄 Files Reviewed: 12
🔍 Findings: 8 total (2 high, 4 medium, 2 low)

High Severity (requires attention):
  1. services/auth-api/src/login.py:45 - No rate limiting on login endpoint
  2. services/data-api/src/query.py:128 - SQL injection vulnerability

Medium Severity (review at next checkpoint):
  3. services/auth-api/src/middleware.py:23 - Blocking HTTP call
  4. services/websocket/src/handler.py:67 - Missing error handling
  ... 2 more

📊 Full report: docs/qa/background/1.3-20250124-103045.yml
```

## Configuration

```yaml
# .bmad-core/core-config.yaml

qa:
  background_review:
    enabled: true
    log_location: docs/qa/background

    # When to auto-start
    auto_start_conditions:
      min_tasks: 5           # Only for stories with 5+ tasks
      estimated_hours: 2     # Or estimated >2 hours

    # Review triggers
    file_patterns:
      - "**/*.py"
      - "**/*.ts"
      - "**/*.tsx"
      - "**/*.js"

    exclude_patterns:
      - "**/tests/**"        # Don't review test files in background
      - "**/migrations/**"
      - "**/__pycache__/**"

    # Debouncing
    debounce_seconds: 5      # Wait 5s after last change before review

    # Notification thresholds
    notify_severity:
      - high                 # Immediately notify on high severity

    # AI Config
    ai_config:
      model: "claude-sonnet-4-5"
      max_tokens: 2000       # Shorter for file-level reviews
      temperature: 0.0
      batch_files: true      # Review multiple files in one call if queued

    # Performance
    cache_ttl: 3600          # Cache review for 1 hour (same file hash)
    max_queue_size: 50       # Prevent runaway queue
```

## Benefits

1. **Non-blocking** - Dev doesn't wait for reviews
2. **Real-time** - Critical issues flagged immediately
3. **Context preservation** - Reviews happen while code fresh in mind
4. **Accumulates evidence** - Background findings feed final QA
5. **Performance-aware** - Uses CLAUDE.md for HomeIQ-specific checks

## Trade-offs

**Pros:**
- Zero interruption to dev flow
- Catches issues early
- Parallel review + development

**Cons:**
- Requires API calls during development (cost)
- May flag false positives (cached until checkpoint)
- Needs file system monitoring

## Resource Management

**API Cost Control:**

```yaml
background_review:
  cost_controls:
    max_reviews_per_hour: 30        # Rate limit API calls
    batch_threshold: 3              # Batch if 3+ files changed
    skip_minor_changes: true        # Skip changes <10 lines
    cache_aggressive: true          # Cache reviews for 1 hour
```

**Expected API usage:**
- Average story: 10-20 background reviews
- Cost: ~$0.50-1.00 per story (at Claude Sonnet pricing)
- ROI: Catches 1-2 critical issues per story before QA

## Example Session

```
10:30 - Dev starts *develop-story
        → Background reviewer starts watching

10:35 - Dev modifies login.py
        → Queued for review (5s debounce)

10:40 - Review completes
        → Finding: HIGH - No rate limiting
        → Notification appears in debug log

10:45 - Dev sees notification
        → Decides to fix immediately
        → Modifies file

10:50 - Review re-runs
        → Finding: PASS - Rate limiting added
        → Cache updated

14:00 - Dev completes all tasks
        → Background reviewer stops
        → Consolidates 8 findings from session
        → Feeds into task completion review

14:15 - Final QA review
        → References background findings
        → Verifies fixes were applied
        → Creates gate decision
```

## Key Principles

- **Asynchronous** - Never block developer
- **Smart caching** - Don't re-review unchanged code
- **Severity-aware** - Notify HIGH, defer others
- **Cost-conscious** - Batch and cache aggressively
- **Evidence-based** - Accumulate findings for final QA
