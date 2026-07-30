---
alwaysApply: true
---
# Agent Autonomy Defaults (TappsMCP)

**Default: NO human-in-the-loop for routine in-scope work.** Decide and act. Do not insert "Ask the user" / "Confirm with user" pauses into flows the user already requested.

This rule overrides the generic Claude Code default of "ask before acting." The user installed TappsMCP precisely so the agent runs autonomously inside the bounded scope defined by `agent-scope.md`.

## What this means

- When the user asks for X (e.g. "create a Linear epic for Y", "open a story for Z", "ship this PR"), do X. Do not echo the plan back and wait for a second confirmation.
- Skip "should I proceed?" prompts on routine in-scope writes: Linear epic/story/issue creation for THIS team+project, file edits in this repo, branch creation in this repo, scoped commits.
- Treat the user's original request as standing authorization for every step in a generator → validator → save_issue chain. Don't pause between the validator and the save.
- Print the final result; don't print mid-flow checkpoints that exist only to elicit a thumbs-up.

## Linear: assignee MUST be the agent, not a human

When creating or updating a Linear epic, story, or issue:

1. Resolve the agent user once per session: call `mcp__plugin_linear_linear__list_users` and select the account whose `name`, `displayName`, or `email` matches `agent`, `bot`, `tapps`, `claude`, or the `agent_user` value in `.tapps-mcp.yaml`. Cache the id for subsequent writes in the same session.
2. Pass `assignee="<agent-user-id-or-name>"` to `mcp__plugin_linear_linear__save_issue` for every create or update.
3. If no agent user exists in the team, leave `assignee` unset. **NEVER fall back to the OAuth user** — that is the human who installed the credential, not the agent doing the work.
4. The same rule applies to subtasks, child stories under an epic, and bulk triage writes. Default = agent. Human assignees only when the user explicitly names a person.

The OAuth-credential human is not the agent. Auto-assigning to them creates false ownership signals and dumps the agent's work onto a human queue.

## Still ask first (the no-HITL default does NOT cover these)

- **Destructive or hard-to-reverse ops**: force-push, deleting branches, dropping tables, `rm -rf`, overwriting uncommitted changes, amending published commits, removing dependencies.
- **Cross-project writes**: see `agent-scope.md`. Writes outside this repo's team/project still require confirmation.
- **External communications**: Slack/email/social posts, GitHub Discussions outside the issue tracker.
- **First-of-its-kind structural decisions** the user did not direct (picking a brand-new architecture, renaming a public API, changing a public contract).
- **Anything explicitly flagged "ask first"** by another rule, the user, or the issue body.

## How to apply

Before writing "Ask the user whether to..." or "Confirm with user before..." in a plan or skill flow, check:

1. Is the action in scope (this repo's team/project)?
2. Is it reversible (or routine enough that "undo" is a normal next step)?
3. Did the user ask for it (or for the broader task it falls under)?

If yes to all three, just do it. If any answer is no, then ask.
