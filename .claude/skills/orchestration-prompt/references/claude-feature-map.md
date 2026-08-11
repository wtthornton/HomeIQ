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
| **AgentForge agent / workflow** | Durable, versioned, published cognition running on the AF platform — survives the session, is Git-authored and independently invocable | Domain reasoning a project needs repeatedly: authoring, judging, analysis. **Where a project's agents should live**, rather than as LLM calls inside its own services | AF cannot see your repo or network — collect source locally and pass it as a declared workflow input. Side effects stay in the consumer |
| **AgentForge `expert-*` agents** | Pre-published platform experts (architecture, testing, security, performance, database, api-design, observability, …) | A second opinion during planning or review, at no authoring cost | They return analysis, not actions. Record where you *rejected* the advice and why |
| **brain / `tapps_memory`** | Shared episodic+semantic memory (per-repo `project_id`) | Recall prior attempts; avoid rediscovery | Cross-project recall needs an explicit `project_id` |

## Model-tier selector — concrete parameters, not adjectives

"cheap tier" is not a dispatchable instruction. Emit the literal parameter values.

**Where each parameter is accepted (check before writing a dispatch line):**

| Caller | `agentType` | `model` | `effort` |
|---|---|---|---|
| **Agent tool** | `subagent_type:` | `model:` — `haiku` \| `sonnet` \| `opus` \| `fable` | **not accepted** — inherits the session's effort |
| **Workflow `agent()`** | `opts.agentType` | `opts.model` | `opts.effort` — `low` \| `medium` \| `high` \| `xhigh` \| `max` |

Consequence worth designing around: **if per-step effort matters, the chunk belongs
in a Workflow**, because the Agent tool cannot set it. Reaching for the Agent tool and
writing "use high effort" in the prose does nothing.

| The chunk is… | agentType | model | effort | Why |
|---|---|---|---|---|
| Poll a status, fetch a file, run a fixed command | `Explore` | `haiku` | `low` | Deterministic; no judgement |
| Mechanical fan-out, read/summarize, inventory | `Explore` | `haiku` | `low` | Read-only by construction |
| Codemod / rename / mechanical edit | `general-purpose` | `sonnet` | `low` | Needs write tools; low judgement |
| Multi-file research needing synthesis | `Explore` | `sonnet` | `medium` | Judgement in what matters, not what exists |
| Hard reasoning, ambiguous fix, architecture | `general-purpose` | `opus` | `high` | Load-bearing judgement |
| **Independent verify / judge** | `general-purpose` | `opus` | `high`–`xhigh` | A weak verifier defeats the whole pattern |
| Adversarial refute on an irreversible step | `general-purpose` | `opus` | `xhigh`–`max` | Cost of a wrong pass is unrecoverable |

Running the harness cheap and spending the strong model only on reasoning + verify is
exactly how a modest base model reaches frontier-level reliability.

## What a cheap model may decide (measured, not assumed)

Model tier must track **the shape of the question**, not the size of the output.

- **Safe on `haiku`:** closed questions with a mechanical answer — "does step X report
  success?", "which files match?", "is this value present?". A wrong answer is
  visible immediately because the evidence is right there.
- **Not safe on `haiku`:** open-ended judgement that *gates* an action — "is CI OK?",
  "is this change safe to merge?", "did anything regress?". Observed failure mode:
  a cheap verifier returned "NO NEW FAILURES FROM THIS PR" while a check on the exact
  changed path was failing *because of that PR*, having skipped the log-fetch step it
  was told to run. It reasoned backwards from the desired conclusion.

**Rule:** narrow the question until a cheap model can answer it from evidence, or pay
for a strong one. Never let a cheap model render a verdict that gates an irreversible
step. If a cheap agent's answer *is* load-bearing, the orchestrator re-derives the
conclusion from the evidence the agent returned, rather than accepting its verdict.

## Agent type is a permission boundary, not a label

`general-purpose` carries Edit/Write **even when the prompt says "read-only"** — a
research agent once silently modified a source file during a prompt-writing turn.
`Explore` has no write tools at all. For genuinely read-only work, pick `Explore` and
let the tool boundary enforce it; prose does not. After any fan-out that used
`general-purpose`, check `git status` before trusting the tree.

## `/goal` vs `/loop`

- `/goal` = **drive one job to done.** Condition-checked, self-terminating.
- `/loop` = **poll/repeat on a cadence.** No notion of "done".
- Recurring autonomous work that must survive the terminal → **Routine** (or
  `claude -p`+cron), not `/loop`.

## Anti-patterns to encode against

- **Inventing a Goal under fog** → refuse; `/tapps-wayfind` until the route is clear.
- One enormous goal → sequence narrow sub-goals.
- Unbounded loop (no cap/budget) → always set max iterations or a token budget.
- **Self-verification only** → add an independent, adversarial verifier (creator ≠ verifier).
- Paying frontier rates for mechanical fan-out → tier the model per chunk.
- Parallel agents on coupled code → sequential per-repo dispatch (serial writes).
- Vague done-condition → demonstrable, ground-truth-anchored condition.
- Context rot (re-reading the same files each iteration) → prune + targeted grep.
- **Features before a validation contract** → write behavioral assertions first when
  changing software behavior; map sub-goals to `fulfills` IDs.
- **Forcing attempt-1 green** → expected-fail fix loop with attempt cap; scoped fix
  sub-goals; never weaken the contract to pass.
- Unstructured "done" handoffs → record completed / undone / commands+exit codes / issues.

## Missions → orchestration-prompt (what we steal, what we don't)

Factory Missions ([architecture](https://factory.ai/news/missions-architecture)) is a
multi-day product runtime. This skill emits **prompts**, not a Missions runner.
Steal the control loop; skip Mission Control UI, computer-use fleets, and
multi-day orchestrators:

| Missions idea | Emit in the prompt as… |
|---|---|
| Validation contract before features | Validation contract table + Done-when = all IDs green |
| Creator ≠ verifier | Fresh verifier subagent; verifier does not implement fixes |
| Scrutiny + user-testing | Deterministic checks + behavioral smoke against assertions |
| Serial feature execution | Serial writes / one repo at a time; parallel read-only OK |
| Structured handoffs | Record fields: completed · undone · cmds+exits · issues |
| Fix features after fail | Expected-fail fix loop ≤3 rounds, then escalate/stop |
