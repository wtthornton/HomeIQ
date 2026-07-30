---
name: linear-issue
user-invocable: true
model: claude-haiku-4-5-20251001
description: Create, lint, validate, or triage Linear issues and epics for agents. MANDATORY for all Linear writes — never call plugin save_issue directly. Routes to docs-mcp generator/validator/triage tools and the Linear plugin by user intent. Use when creating, linting, validating, or triaging a Linear issue or epic.
allowed-tools: mcp__nlt-linear-issues__docs_generate_epic mcp__nlt-linear-issues__docs_generate_story mcp__nlt-linear-issues__docs_lint_linear_issue mcp__nlt-linear-issues__docs_validate_linear_issue mcp__nlt-linear-issues__docs_linear_triage mcp__nlt-linear-issues__docs_save_linear_issue mcp__plugin_linear_linear__save_issue mcp__plugin_linear_linear__get_issue mcp__plugin_linear_linear__list_issues mcp__nlt-linear-issues__tapps_linear_snapshot_get mcp__nlt-linear-issues__tapps_linear_snapshot_put mcp__nlt-linear-issues__tapps_linear_snapshot_invalidate
argument-hint: "[create-epic|create-story|lint TAP-###|validate|triage] [free-form detail]"
---

Work with Linear issues for AI-agent consumption. Infer intent from the user's prompt and act autonomously within scope — see `autonomy.md`. The user's original request is the authorization for the full generator → validator → save_issue chain; do NOT pause mid-flow to ask "should I create this?"

**When to invoke this skill:** ANY request that will create, update, or validate a Linear issue or epic. This includes "file a ticket", "create an issue", "open an epic", "track this as a story", or "add a bug report to Linear". Raw `save_issue` calls are a rule violation — route through this skill.

**Assignee — agent, not human (applies to every write below).** Resolve the agent user once per session via `mcp__plugin_linear_linear__list_users`, picking the user whose `name`/`displayName`/`email` matches `agent`, `bot`, `tapps`, `claude`, or `agent_user` in `.tapps-mcp.yaml`. Cache the id. Pass `assignee="<agent-user-id-or-name>"` on every `save_issue`. If no agent user exists, leave `assignee` unset — never fall back to the OAuth user (the human running the session). Only override when the user explicitly names a person.

**Create an epic** (prompt names multiple stories, or "epic", or spans a cross-cutting initiative):
1. Call `mcp__nlt-linear-issues__docs_generate_epic` with the user's ask. Required: `title`, `purpose_and_intent` ("We are doing this so that ..."), `goal`, `motivation`, `acceptance_criteria`, `stories` (JSON array). Optional: `priority`, `estimated_loe`, `references`, `non_goals`.
2. Use `data.content` from the generator response (default `write_to_disk=false` — no repo file). Do NOT read epic markdown from disk.
3. Build the Linear-body markdown following the 5-to-7 section epic shape: `## Purpose & Intent`, `## Goal`, `## Motivation`, `## Acceptance Criteria`, `## Stories`, `## Out of Scope`, `## Refs`.
4. Validate via `mcp__nlt-linear-issues__docs_validate_linear_issue(title, description, priority, is_epic=true)`. Target score 100 / `agent_ready=true`.
5. Call `mcp__nlt-linear-issues__docs_save_linear_issue(title=<title>, description=<description>)` as the server-side pre-save gate (TAP-2009). If `data.ok: true`, call `mcp__plugin_linear_linear__save_issue(team, project, title, description, priority, assignee="<agent-user-id-or-name>", ...)` without `id`. If `data.ok: false`, re-validate per the refusal envelope's `use`/`args` fields then retry this step.
6. Create each child story via the create-story flow below, passing `parent_id=<epic TAP-id>` (each child is also assigned to the agent).
7. After all writes, call `mcp__nlt-linear-issues__tapps_linear_snapshot_invalidate(team, project)`.

**Create a story** (default when prompt describes a single change/bug):
1. Call `mcp__nlt-linear-issues__docs_generate_story` with the user's ask. Required: `title` (<=80 chars, pattern `file.py: symptom`), `files` (comma-separated, each with `:LINE-RANGE`), `acceptance_criteria` (verifiable items).
2. Default `audience="agent"` emits the 5-section Linear template (What/Where/Why/Acceptance/Refs) and round-trips through the validator.
3. If the call returns `INPUT_INVALID`, refine the inputs per the error message and retry. Do NOT pass `audience="human"` unless the user asks for a product-review doc.
4. Call `mcp__nlt-linear-issues__docs_save_linear_issue(title=<title>, description=<description>)` as the server-side pre-save gate (TAP-2009). If `data.ok: true`, call `mcp__plugin_linear_linear__save_issue(..., assignee="<agent-user-id-or-name>", parent_id=<epic-id-if-any>)`. If `data.ok: false`, re-validate with `docs_validate_linear_issue` per the refusal envelope's `use`/`args` fields, then retry this step.
5. After `save_issue` returns, call `mcp__nlt-linear-issues__tapps_linear_snapshot_invalidate(team=<team>, project=<project>)` to evict stale cached snapshots for that slice.

**Lint** an existing issue (prompt like "lint TAP-686", "check TAP-###"):
1. Fetch via `mcp__plugin_linear_linear__get_issue`.
2. Pass title/description/labels/priority/estimate to `mcp__nlt-linear-issues__docs_lint_linear_issue`.
3. Surface score, findings (with fix_hints), and reclaimable noise bytes. For each HIGH severity finding, quote the suggested fix.

**Validate** before creating or after editing (prompt like "is this agent-ready?"):
1. Call `mcp__nlt-linear-issues__docs_validate_linear_issue` with the payload.
2. Report `{agent_ready, score, missing[]}`. Missing items are blockers; propose a concrete fix per item.

**Triage** a batch (prompt like "triage open issues", "find label gaps"):
1. If the user names a specific issue (e.g. "triage TAP-686"), use `mcp__plugin_linear_linear__get_issue(id="TAP-686")` — skip list/cache entirely.
2. **Cache-first read:** call `mcp__nlt-linear-issues__tapps_linear_snapshot_get(team=<team>, project=<project>, state="backlog" | "unstarted", label?)`. If `data.cached` is `true`, use `data.issues` directly — Linear was not called.
3. **On cache miss** (`data.cached` is `false`): call `mcp__plugin_linear_linear__list_issues` with narrow filters — `team`, `project`, `state`, `includeArchived=false` (never call without filters). Then populate the cache by calling `mcp__nlt-linear-issues__tapps_linear_snapshot_put(team, project, issues_json=json.dumps(response.issues), state, label?)` using the **same** team/project/state/label/limit as the get call so the keys align.
4. Pass the list to `mcp__nlt-linear-issues__docs_linear_triage`.
5. Apply label_proposals, parent_groupings, and metadata_gaps via Linear plugin writes (each `save_issue` carries `assignee="<agent-user-id-or-name>"` for any newly-owned items). No mid-flow user confirmation; the triage request is the authorization.
6. After any write, call `mcp__nlt-linear-issues__tapps_linear_snapshot_invalidate(team=<team>, project=<project>)` to refresh the cache on next read.

Rules (enforced by docs-mcp tools):
- Title <=80 chars; no em-dash preambles.
- Inline-code filenames (`AGENTS.md`), never `[AGENTS.md](AGENTS.md)` (Linear's autolinker mangles).
- Bare `TAP-###` refs, never `<issue id="UUID">TAP-###</issue>` wrappers.
- `## Acceptance` has at least one verifiable `- [ ]` item.
- `## Where` includes at least one `path/to/file.ext:LINE-RANGE` anchor.

Linear rendering workarounds (observed 2026-04-24):
- **Use numbered lists, not bulleted lists, in `## Where` and `## Acceptance` when items reference file paths.** Linear's markdown engine silently drops multiple bulleted `* path/...` entries (appears to dedupe on auto-linked filenames, especially `.md` files), keeping only the first. Numbered lists (`1.`, `2.`, ...) survive.
- **Wrap file paths in backticks** when they appear in list items: `` `path/to/file.py:1-100` `` rather than bare `path/to/file.py:1-100`. Prevents auto-linking that contributes to the dedupe bug.
- **Avoid raw `.md` filenames in bulleted prose.** Refer to "the agents-md template" or "the claude-md file" when the plain word would trigger auto-linking in a context that loses data. Inline-code with backticks is safe.
- **Tables with multiple columns** are fragile in Linear; prefer numbered lists with `—` separators for compact multi-field rows.
