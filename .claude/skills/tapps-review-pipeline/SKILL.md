---
name: tapps-review-pipeline
user-invocable: true
model: claude-sonnet-4-6
description: >-
  Orchestrate a parallel review-fix-validate pipeline across multiple changed files.
  Spawns tapps-review-fixer agents in worktrees for parallel processing.
allowed-tools: mcp__tapps-mcp__tapps_validate_changed mcp__tapps-mcp__tapps_checklist
context: fork
agent: general-purpose
---

Run a parallel review-fix-validate pipeline on changed Python files:

1. Call `mcp__tapps-mcp__tapps_session_start` if not already called
2. Determine scope: detect changed Python files via git diff or accept a file list
3. For each file (or batch of files), spawn a `tapps-review-fixer` agent in a worktree:
   - Use the Task tool with `subagent_type: "general-purpose"` and `isolation: "worktree"`
   - Pass the file path and instructions to score, fix, and gate the file
4. Wait for all agents to complete and collect their results
5. Merge any worktree changes back (review diffs before accepting)
6. Call `mcp__tapps-mcp__tapps_validate_changed` with explicit `file_paths` to verify all files pass
7. Call `mcp__tapps-mcp__tapps_checklist(task_type="review")` for final verification
8. Present a summary table: file | before score | after score | gate | fixes applied
