"""View-model for the AgentForge ops page: pure row/status builders.

Kept out of the Streamlit page module so the display rules are testable without a
UI runtime — the page is then only rendering.
"""

from pathlib import Path

WARN_FRACTION = 0.8
GATE_ROWS_SHOWN = 50


def repo_root(start: Path | None = None) -> Path:
    """The checkout root (the agent budgets live under it), found by walking up to `.git`."""
    current = (start or Path(__file__)).resolve()
    for parent in current.parents:
        if (parent / ".git").exists():
            return parent
    return current.parent


def budget_status(spent_usd: float, cap_usd: float | None) -> str:
    """OVER BUDGET / WARNING / OK for one agent — "—" when no cap is declared."""
    if not cap_usd:
        return "—"
    if spent_usd >= cap_usd:
        return "OVER BUDGET"
    if spent_usd >= cap_usd * WARN_FRACTION:
        return "WARNING"
    return "OK"


def agent_rows(stats: list) -> list[dict[str, object]]:
    """Display rows for the per-agent table."""
    return [
        {
            "Agent": s.agent,
            "Invocations": s.invocation_count,
            "Errors": s.error_count,
            "Budget kills": getattr(s, "over_budget_kills", 0),
            "Total Cost ($)": f"{s.total_cost_usd:.4f}",
            "Avg Cost ($)": f"{s.avg_cost_usd:.4f}",
            "Budget ($)": f"{s.max_budget_usd:.2f}" if s.max_budget_usd else "—",
            "Status": budget_status(s.total_cost_usd, s.max_budget_usd),
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


def budget_lines(budgets: dict[str, float | None], stats: list) -> list[str]:
    """One line per declared cap: `agent: $cap — 🟢/🟡/🔴 pct` (pct only when spend is known)."""
    spent = {s.agent: s.total_cost_usd for s in stats}
    lines = []
    for agent, cap in sorted(budgets.items()):
        used = spent.get(agent)
        marker = "—"
        if cap and used is not None:
            pct = used / cap * 100
            icon = "🔴" if pct >= 100 else "🟡" if pct >= WARN_FRACTION * 100 else "🟢"
            marker = f"{icon} {pct:.0f}%"
        lines.append(f"- {agent}: {f'${cap:.2f}' if cap else 'unset'} — {marker}")
    return lines
