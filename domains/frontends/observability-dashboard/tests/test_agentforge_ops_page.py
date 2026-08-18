"""Pure row/status builders behind the AgentForge ops page."""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.agent_budget_loader import UnreadableCap, load_agent_budgets  # noqa: E402
from services.agentforge_ops_view import (  # noqa: E402
    agent_rows,
    budget_lines,
    budget_status,
    gate_rows,
    repo_root,
)


def _stat(
    agent,
    cost,
    cap,
    invocations=3,
    errors=0,
    kills=0,
    budget_key=None,
    peak=None,
    cap_unreadable=False,
):
    return SimpleNamespace(
        agent=agent,
        budget_key=agent if budget_key is None else budget_key,
        total_cost_usd=cost,
        avg_cost_usd=cost / invocations if invocations else 0.0,
        max_invocation_cost_usd=(cost / invocations if invocations else 0.0)
        if peak is None
        else peak,
        max_budget_usd=cap,
        budget_cap_unreadable=cap_unreadable,
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


def test_budget_status_grades_the_peak_run_against_a_per_invocation_cap():
    """`max_budget_usd` bounds one run, so the peak run is the figure it governs."""
    assert budget_status(0.1, 0.5) == "OK"
    assert budget_status(0.4, 0.5) == "WARNING"  # exactly 80%
    assert budget_status(0.5, 0.5) == "OVER CAP"
    assert budget_status(0.9, 0.5) == "OVER CAP"
    assert budget_status(1.0, None) == "—"  # no declared cap is not "OK"


def test_agent_rows_carry_costs_caps_and_kills():
    (row,) = agent_rows(
        [_stat("hiq-summarize", 0.45, 0.5, invocations=3, errors=1, kills=2, peak=0.4)]
    )
    assert row["Agent"] == "hiq-summarize"
    assert row["Cumulative Cost ($)"] == "0.4500" and row["Cap ($/run)"] == "0.50"
    assert row["Peak Run ($)"] == "0.4000"
    assert row["Status"] == "WARNING" and row["Errors"] == 1 and row["Budget kills"] == 2


def test_agent_rows_do_not_call_cumulative_spend_over_budget():
    """TAP-5321 follow-up: 21 cheap runs summing past a per-run cap refused nothing."""
    (row,) = agent_rows([_stat("homeiq-service-auditor", 7.67, 2.0, invocations=21, peak=0.4231)])

    assert row["Cumulative Cost ($)"] == "7.6700"
    assert row["Status"] == "OK"


def test_agent_rows_render_missing_cap_as_dash():
    (row,) = agent_rows([_stat("homeiq-mcp-probe", 0.2, None)])
    assert row["Cap ($/run)"] == "—" and row["Status"] == "—"


def test_agent_rows_distinguish_an_unreadable_cap_from_an_absent_one():
    """An unreadable cap is unknown, not "no cap" — the latter reads as unlimited spend."""
    (row,) = agent_rows([_stat("hiq-rank", 0.2, None, cap_unreadable=True)])

    assert row["Cap ($/run)"] == "unknown" and row["Status"] == "UNKNOWN CAP"


def test_gate_rows_mark_blocked_and_carry_the_rule():
    rows = gate_rows([_decision("hiq-judge-automation", "blocked", "deny.unlock_lock")])
    assert rows[0]["Decision"].endswith("blocked") and rows[0]["Rule"] == "deny.unlock_lock"
    assert rows[0]["Invocation"].endswith("…")


def test_gate_rows_are_limited():
    assert len(gate_rows([_decision("a", "approved") for _ in range(80)], limit=10)) == 10


def test_gate_rows_do_not_silently_relabel_unknown_decisions():
    (row,) = gate_rows([_decision("a", "error")])
    assert "error" in row["Decision"]


def test_budget_lines_grade_the_peak_run_and_report_cumulative_separately():
    lines = budget_lines(
        {"hiq-summarize": 0.5, "hiq-correlate": 0.5, "hiq-notify": None},
        [_stat("hiq-summarize", 1.65, 0.5, invocations=3, peak=0.55)],
    )
    assert lines[2] == (
        "- hiq-summarize: cap $0.50/run — peak run $0.5500 🔴 110% of cap "
        "— $1.6500 cumulative over 3 runs"
    )
    assert lines[1] == "- hiq-notify: no cap declared — no invocations recorded"
    assert lines[0] == "- hiq-correlate: cap $0.50/run — no invocations recorded"


def test_budget_lines_do_not_read_cumulative_spend_as_a_breach():
    """Many cheap runs summing past a per-run cap is normal, not 🔴."""
    lines = budget_lines(
        {"homeiq-service-auditor": 2.0},
        [_stat("homeiq-service-auditor", 7.67, 2.0, invocations=21, peak=0.4231)],
    )

    assert lines == [
        "- homeiq-service-auditor: cap $2.00/run — peak run $0.4231 🟢 21% of cap "
        "— $7.6700 cumulative over 21 runs"
    ]


def test_budget_lines_report_an_unreadable_cap_as_unreadable():
    lines = budget_lines({"hiq-rank": UnreadableCap(reason="PermissionError: denied")}, [])

    assert lines == [
        "- hiq-rank: cap unreadable (PermissionError: denied) — spend is ungoverned here"
    ]


def test_budget_lines_use_the_budget_key_not_the_namespaced_agent():
    """Spend arrives keyed `homeiq-hiq-summarize`; the cap line is keyed `hiq-summarize`."""
    lines = budget_lines(
        {"hiq-summarize": 0.5},
        [_stat("homeiq-hiq-summarize", 1.65, 0.5, budget_key="hiq-summarize", peak=0.55)],
    )

    assert any("hiq-summarize: cap $0.50/run — peak run $0.5500 🔴 110% of cap" in x for x in lines)


def test_budget_lines_fold_namespaced_and_bare_rows_into_one_gene():
    """Pre- and post-namespace invocations of one gene are a single peak and a single total."""
    lines = budget_lines(
        {"hiq-summarize": 1.0},
        [
            _stat("hiq-summarize", 0.4, 1.0, invocations=1, peak=0.4),
            _stat(
                "homeiq-hiq-summarize",
                0.9,
                1.0,
                budget_key="hiq-summarize",
                invocations=1,
                peak=0.9,
            ),
        ],
    )

    assert lines == [
        "- hiq-summarize: cap $1.00/run — peak run $0.9000 🟡 90% of cap "
        "— $1.3000 cumulative over 2 runs"
    ]


def test_every_gene_in_the_checkout_declares_a_readable_cap():
    """TAP-5321: an undeclared cap is unlimited spend, so the fleet must be complete."""
    budgets = load_agent_budgets(repo_root())

    assert budgets, "no agent definitions found under agentforge/projects/homeiq/agents"
    assert [name for name, cap in budgets.items() if not isinstance(cap, float) or not cap] == []


def test_repo_root_finds_the_checkout():
    root = repo_root()
    assert (root / ".git").exists()
    assert (root / "agentforge" / "projects" / "homeiq" / "agents").is_dir()
