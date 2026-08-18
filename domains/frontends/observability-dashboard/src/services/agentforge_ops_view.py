"""View-model for the AgentForge ops page: pure row/status builders.

Kept out of the Streamlit page module so the display rules are testable without a
UI runtime — the page is then only rendering.

One semantic runs through every builder here: `max_budget_usd` is AgentForge's
**per-invocation** ceiling (`backend/executor/llm_auth_budget.py`), so the only spend
figure it can be compared against is the costliest single run. Cumulative spend is
reported alongside it as its own, uncapped figure — never as a breach.
"""

from pathlib import Path

from services.agent_budget_loader import BudgetCap, UnreadableCap

WARN_FRACTION = 0.8
GATE_ROWS_SHOWN = 50


def repo_root(start: Path | None = None) -> Path:
    """The checkout root (the agent budgets live under it), found by walking up to `.git`."""
    current = (start or Path(__file__)).resolve()
    for parent in current.parents:
        if (parent / ".git").exists():
            return parent
    return current.parent


def budget_status(peak_invocation_usd: float, cap_usd: float | None) -> str:
    """OVER CAP / WARNING / OK for the agent's costliest single invocation.

    `cap_usd` bounds one run, so this compares it against the peak run — never against
    cumulative spend, which crosses a per-invocation cap routinely without any
    invocation having been refused. Returns "—" when no cap is declared.
    """
    if not cap_usd:
        return "—"
    if peak_invocation_usd >= cap_usd:
        return "OVER CAP"
    if peak_invocation_usd >= cap_usd * WARN_FRACTION:
        return "WARNING"
    return "OK"


def cap_display(cap_usd: float | None, unreadable: bool) -> str:
    """The cap cell: the declared per-run figure, "unknown" on a read failure, else "—"."""
    if unreadable:
        return "unknown"
    return f"{cap_usd:.2f}" if cap_usd else "—"


def agent_rows(stats: list) -> list[dict[str, object]]:
    """Display rows for the per-agent table."""
    return [
        {
            "Agent": s.agent,
            "Invocations": s.invocation_count,
            "Errors": s.error_count,
            "Budget kills": getattr(s, "over_budget_kills", 0),
            "Cumulative Cost ($)": f"{s.total_cost_usd:.4f}",
            "Avg Cost ($)": f"{s.avg_cost_usd:.4f}",
            "Peak Run ($)": f"{s.max_invocation_cost_usd:.4f}",
            "Cap ($/run)": cap_display(
                s.max_budget_usd, getattr(s, "budget_cap_unreadable", False)
            ),
            "Status": "UNKNOWN CAP"
            if getattr(s, "budget_cap_unreadable", False)
            else budget_status(s.max_invocation_cost_usd, s.max_budget_usd),
        }
        for s in stats
    ]


def gate_rows(decisions: list, limit: int = GATE_ROWS_SHOWN) -> list[dict[str, object]]:
    """Display rows for the gate-decision table, most recent first."""
    return [
        {
            "Invocation": d.invocation_id[:12] + "…",
            "Agent": d.agent,
            "Decision": {"approved": "✅ approved", "blocked": "❌ blocked"}.get(
                d.decision, f"⚠️ {d.decision}"
            ),
            "Rule": d.rule_id or "—",
            "Cost ($)": f"{d.cost_usd:.4f}",
            "When": d.timestamp,
        }
        for d in decisions[:limit]
    ]


def _usage_text(peak: float, total: float, runs: int, cap: float | None) -> str:
    """The spend half of a budget line: peak run against the cap, then cumulative apart."""
    if runs == 0:
        return "no invocations recorded"
    headroom = ""
    if cap:
        pct = peak / cap * 100
        icon = "🔴" if pct >= 100 else "🟡" if pct >= WARN_FRACTION * 100 else "🟢"
        headroom = f" {icon} {pct:.0f}% of cap"
    plural = "" if runs == 1 else "s"
    return f"peak run ${peak:.4f}{headroom} — ${total:.4f} cumulative over {runs} run{plural}"


def budget_lines(budgets: dict[str, BudgetCap], stats: list) -> list[str]:
    """One line per gene: its per-run cap, its peak run against that cap, and — separately
    — cumulative spend, which no cap in this project bounds.

    Spend is keyed on `AgentStats.budget_key` — the gene filename the cap was matched
    on — because `budgets` uses filenames while an invocation's `agent` carries AF's
    project namespace prefix. Falls back to `agent` for stat objects without the field.
    """
    totals: dict[str, float] = {}
    peaks: dict[str, float] = {}
    runs: dict[str, int] = {}
    for s in stats:
        key = getattr(s, "budget_key", "") or s.agent
        totals[key] = totals.get(key, 0.0) + s.total_cost_usd
        peaks[key] = max(peaks.get(key, 0.0), s.max_invocation_cost_usd)
        runs[key] = runs.get(key, 0) + s.invocation_count

    lines = []
    for agent, cap in sorted(budgets.items()):
        if isinstance(cap, UnreadableCap):
            lines.append(f"- {agent}: cap unreadable ({cap.reason}) — spend is ungoverned here")
            continue
        cap_text = f"cap ${cap:.2f}/run" if cap else "no cap declared"
        usage = _usage_text(peaks.get(agent, 0.0), totals.get(agent, 0.0), runs.get(agent, 0), cap)
        lines.append(f"- {agent}: {cap_text} — {usage}")
    return lines
