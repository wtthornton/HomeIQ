# TappsMCP Feedback Log

> Persistent structured feedback for TappsMCP tool improvement.
> Each auto-bugfix run appends an entry. Entries are removed once addressed.
> Goal: this file stays empty — meaning TappsMCP is working perfectly.

## How to Read This File

- **Entries below** are observations from automated and manual sessions
- Each entry has a category, severity, and actionable description
- Once the TappsMCP team addresses an item, delete the entry
- If an item recurs after deletion, it wasn't fully fixed — re-add with `recurrence: N`

## Categories

| Tag | Meaning |
|-----|---------|
| `BUG` | Tool returned incorrect/broken output |
| `FALSE_POSITIVE` | Tool flagged something that isn't a real issue |
| `FALSE_NEGATIVE` | Tool missed something it should have caught |
| `UX` | Confusing output, unclear next_steps, bad formatting |
| `PERF` | Tool was too slow or timed out |
| `ENHANCEMENT` | Feature request or improvement idea |
| `INTEGRATION` | Issue using tool in headless/scripted mode |

## Severity

| Level | Meaning |
|-------|---------|
| `P0` | Blocks workflow — must fix |
| `P1` | Degrades quality — should fix soon |
| `P2` | Minor friction — fix when convenient |

---

<!-- FEEDBACK ENTRIES BELOW — newest first -->
<!-- Delete entries once addressed by TappsMCP -->

