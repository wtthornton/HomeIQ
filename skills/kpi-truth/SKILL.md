---
name: kpi-truth
description: Use when joining store metrics across sources, deciding which source is authoritative for a field, or interpreting a discrepancy between platforms.
version: 1.0.0
allowed_tools: ""
---
# KPI truth — source authority and what a discrepancy means

Two sources will disagree about revenue. Neither is lying, and averaging them
produces a number that is true nowhere.

## Authority per field

| Field class | Authoritative source | Never authoritative |
| --- | --- | --- |
| Revenue, orders, refunds, taxes collected | Commerce platform | Analytics property, ad platform |
| Sessions, traffic source, on-site behaviour | Analytics property | Commerce platform |
| Impressions, clicks, spend | Ad platform | Anything else |
| Conversions attributed to a campaign, ROAS | **Nothing** — see below | Ad platform (systematically overstates) |
| Reach, engagement, saves | The channel that hosts the post | — |
| Inventory on hand | Commerce platform | Any cached copy |

## Expected discrepancies — do not raise these as anomalies

- **Commerce revenue vs analytics revenue** routinely differs by low tens of
  percent. Causes are structural: ad blockers, consent mode, cross-device,
  bot filtering, refund timing, currency rounding, timezone boundaries.
  Report the delta; mark it `expected: true`.
- **Ad-platform conversions vs actual orders** differ by more, and in a
  predictable direction: platforms claim credit generously and de-duplicate
  poorly across channels.
- **Analytics transactions = 0 while orders > 0** is *not* an expected
  discrepancy. That is a tracking failure and it is the first hypothesis.

## Platform-reported ROAS is an untrusted input

It may be ingested, must be labelled untrusted, and must never be the objective
a gene optimizes. When derived metrics become computable, the objective is
first-party: money in from the commerce platform against total spend across all
channels, and contribution margin where cost data exists.

**Anti-Goodhart rule.** A gene that moves a metric is never judged on that
metric. Pacing is judged on downstream first-party return and refund rate,
computed by a different gene from a different source.

## Phase 0 limits, stated plainly

Phase 0 reports only what the platforms themselves computed, joins it, and
names conflicts. It does **not** derive blended metrics, run statistical
baselines, or compute margin — a Pattern A consumer project currently has no
deterministic compute surface, and doing money math inside an LLM is the wrong
trade. Say "not computed in Phase 0" rather than estimating.

## Presentation rules

1. Every figure carries its unit, its window, and its source.
2. Never round currency into vagueness ("about a thousand").
3. A metric from an unavailable source is absent and named as absent — never
   carried forward from yesterday, never imputed.
4. Percentages state their base ("conversion 2.1% of 410 sessions").
