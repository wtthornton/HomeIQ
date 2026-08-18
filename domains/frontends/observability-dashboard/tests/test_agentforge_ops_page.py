"""Pure row/status builders behind the AgentForge ops page."""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.agentforge_ops_view import (  # noqa: E402
    agent_rows,
    budget_lines,
    budget_status,
    gate_rows,
    repo_root,
)


def _stat(agent, cost, cap, invocations=3, errors=0, kills=0):
    return SimpleNamespace(
        agent=agent,
        total_cost_usd=cost,
        avg_cost_usd=cost / invocations if invocations else 0.0,
        max_budget_usd=cap,
        invocation_count=invocations,
        error_count=errors,
        over_budget_kills=kills,
    )


def _decision(agent, decision, rule=None, cost=0.1):
    return SimpleNamespace(
        invocation_id="8e905a10-05a5-4c6f-8dec-5e97ddb32dd2",
        agent=agent,
        decision=decision,
        rule_id=rule,
        cost_usd=cost,
        timestamp="2026-08-18T06:00:00Z",
    )


def test_budget_status_thresholds():
    assert budget_status(0.1, 0.5) == "OK"
    assert budget_status(0.4, 0.5) == "WARNING"  # exactly 80%
    assert budget_status(0.5, 0.5) == "OVER BUDGET"
    assert budget_status(0.9, 0.5) == "OVER BUDGET"
    assert budget_status(1.0, None) == "—"  # no declared cap is not "OK"


def test_agent_rows_carry_costs_caps_and_kills():
    (row,) = agent_rows([_stat("hiq-summarize", 0.45, 0.5, invocations=3, errors=1, kills=2)])
    assert row["Agent"] == "hiq-summarize"
    assert row["Total Cost ($)"] == "0.4500" and row["Budget ($)"] == "0.50"
    assert row["Status"] == "WARNING" and row["Errors"] == 1 and row["Budget kills"] == 2


def test_agent_rows_render_missing_cap_as_dash():
    (row,) = agent_rows([_stat("homeiq-mcp-probe", 0.2, None)])
    assert row["Budget ($)"] == "—" and row["Status"] == "—"


def test_gate_rows_mark_blocked_and_carry_the_rule():
    rows = gate_rows([_decision("hiq-judge-automation", "blocked", "deny.unlock_lock")])
    assert rows[0]["Decision"].endswith("blocked") and rows[0]["Rule"] == "deny.unlock_lock"
    assert rows[0]["Invocation"].endswith("…")


def test_gate_rows_are_limited():
    assert len(gate_rows([_decision("a", "approved") for _ in range(80)], limit=10)) == 10


def test_gate_rows_do_not_silently_relabel_unknown_decisions():
    (row,) = gate_rows([_decision("a", "error")])
    assert "error" in row["Decision"]


def test_budget_lines_pct_only_when_spend_is_known():
    lines = budget_lines(
        {"hiq-summarize": 0.5, "hiq-correlate": 0.5, "hiq-notify": None},
        [_stat("hiq-summarize", 0.55, 0.5)],
    )
    assert any("hiq-summarize: $0.50 — 🔴 110%" in line for line in lines)
    assert any(line == "- hiq-correlate: $0.50 — —" for line in lines)  # no spend, no pct
    assert any("hiq-notify: unset" in line for line in lines)


def test_repo_root_finds_the_checkout():
    root = repo_root()
    assert (root / ".git").exists()
    assert (root / "agentforge" / "projects" / "homeiq" / "agents").is_dir()
