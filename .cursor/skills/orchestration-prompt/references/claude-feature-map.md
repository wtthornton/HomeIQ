# Claude feature map — intent → mechanism → model tier

Read this when choosing how a chunk of an orchestration prompt should run. Put each
step on the cheapest, most durable mechanism that fits — and the cheapest model tier
that still gets it right. Spend the frontier model only where judgement is
load-bearing (hard reasoning, and the independent verify/judge step).

## The two planes

- **Coordination plane** (research/audit/triage/synthesis/dispatch/**verification**):
  fan-out is good — you can usefully spend tokens in parallel. Token-spend-in-parallel
  is the test for whether to fan out at all.
- **Execution plane** (writing code): sequential, one repo at a time. Coupled coding
  is the worst fit for fan-out (tight dependencies, shared context, error cascade).

## Mechanism catalog

| Mechanism | What it is | Best for | Watch out |
|---|---|---|---|
| **`/goal <condition>`** | Drives turn-after-turn until a fast model judges the condition met (against Claude's *surfaced output*, not by running commands) | One job to a provable finish | Condition must be demonstrable + ground-truth-anchored; decompose large goals |
| **`/loop [interval] <prompt>`** | Re-runs a prompt on a timer / each turn | Polling, babysitting a build/PR | Session-bound — dies with the terminal; never your durable layer |
| **Scheduled Routine** | Saved config run on cloud cron | "Nightly: take top backlog item, open a draft PR" | Keep a human review gate |
| **`claude -p` + cron / CI** | Headless one-shot via external scheduler | Durable recurring runs, zero preview risk | Feature-light; no session persistence |
| **Workflow tool** | Deterministic JS orchestration (`phase/agent/parallel/pipeline`), budget-capped, resumable, per-stage `model`/`effort` | Bounded parallel multi-repo sweeps; fan-out verify | Per-invocation, not a persistent loop |
| **Subagents** | Focused workers in isolated context, report back | 3–5 parallel research/review/**verify** tasks | Don't fan out coupled coding; declare minimal tools |
| **Verifier subagent** | A fresh-context agent prompted to *refute* a claim, re-running the check | Confirming a sub-goal's proof independently of the executor | The whole point is a *different* context — don't reuse the executor |
| **brain / `tapps_memory`** | Shared episodic+semantic memory (per-repo `project_id`) | Recall prior attempts; avoid rediscovery | Cross-project recall needs an explicit `project_id` |

## Model-tier selector

| The chunk is… | Tier |
|---|---|
| Mechanical fan-out, read/summarize, codemod, rename | cheap / low-effort |
| Hard reasoning, ambiguous fix, architecture, design | frontier / high-effort |
| **Independent verify / judge** | **frontier / high-effort** (a weak verifier defeats the pattern) |
| Recurring poll, status check | cheap |

Running the harness cheap and spending the strong model only on reasoning + verify is
exactly how a modest base model reaches frontier-level reliability.

## `/goal` vs `/loop`

- `/goal` = **drive one job to done.** Condition-checked, self-terminating.
- `/loop` = **poll/repeat on a cadence.** No notion of "done".
- Recurring autonomous work that must survive the terminal → **Routine** (or
  `claude -p`+cron), not `/loop`.

## Anti-patterns to encode against

- One enormous goal → sequence narrow sub-goals.
- Unbounded loop (no cap/budget) → always set max iterations or a token budget.
- **Self-verification only** → add an independent, adversarial verifier.
- Paying frontier rates for mechanical fan-out → tier the model per chunk.
- Parallel agents on coupled code → sequential per-repo dispatch.
- Vague done-condition → demonstrable, ground-truth-anchored condition.
- Context rot (re-reading the same files each iteration) → prune + targeted grep.
