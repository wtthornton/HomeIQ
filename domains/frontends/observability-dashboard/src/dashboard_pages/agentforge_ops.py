"""AgentForge operations page: agent spend, gate decisions and budget headroom.

Reads AgentForge over HTTP only (never its database). The row builders below are
pure so they can be tested without Streamlit; `show()` is the thin render shell.
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.append(str(Path(__file__).parent.parent))

from services.agent_budget_loader import BudgetCap, load_agent_budgets  # noqa: E402
from services.agentforge_client import AgentForgeClient  # noqa: E402
from services.agentforge_ops_view import (  # noqa: E402
    agent_rows,
    budget_lines,
    gate_rows,
    repo_root,
)
from utils.async_helpers import run_async_safe  # noqa: E402

from config import settings  # noqa: E402


def _render_spend(spend) -> None:
    st.subheader("Project spend")
    if not spend:
        st.warning("AgentForge returned no spend record for this project")
        return
    cols = st.columns(4)
    cols[0].metric("Total", f"${spend.by_source.total_cost_usd:.2f}")
    cols[1].metric("LLM", f"${spend.by_source.llm_cost_usd:.2f}")
    cols[2].metric("Provider", f"${spend.by_source.provider_cost_usd:.2f}")
    cols[3].metric("Entries", spend.entry_count)


def _render_agents(stats: list) -> None:
    st.subheader("Per-agent spend against declared per-invocation caps")
    if not stats:
        st.info("No invocations recorded for this project yet")
        return
    st.caption(
        "`max_budget_usd` caps a **single invocation**, so Status compares the peak run "
        "against it. Cumulative cost is shown alongside and is bounded by nothing here — "
        "the aggregate ceiling is the AF instance's AF_MONTHLY_BUDGET_USD."
    )
    st.dataframe(pd.DataFrame(agent_rows(stats)), use_container_width=True)
    for s in stats:
        if s.budget_cap_unreadable:
            st.error(
                f"⛔ {s.agent}: its declared cap could not be read, so this page cannot "
                "tell an uncapped gene from an unreadable one — check the gene file."
            )
        elif s.max_budget_usd and s.max_invocation_cost_usd >= s.max_budget_usd:
            st.warning(
                f"⚠️ {s.agent} had a single invocation reach its per-run cap: "
                f"${s.max_invocation_cost_usd:.4f} / ${s.max_budget_usd:.2f}"
            )


def _render_gates(decisions: list) -> None:
    st.subheader("Recent gate decisions")
    if not decisions:
        st.info("No judge verdicts in the recent invocations")
        return
    st.dataframe(pd.DataFrame(gate_rows(decisions)), use_container_width=True)


def _render_budgets(budgets: dict[str, BudgetCap], stats: list) -> None:
    st.subheader("Declared budgets (from the repo's agent frontmatter)")
    if not budgets:
        st.info("No agent declares max_budget_usd in this checkout")
        return
    st.markdown("\n".join(budget_lines(budgets, stats)))
    st.caption(
        "Project-level monthly caps are an AgentForge instance setting "
        "(AF_MONTHLY_BUDGET_USD); unset here — see TAP-5321."
    )


def show() -> None:
    """Render the AgentForge ops page."""
    st.header("🤖 AgentForge Ops")
    st.caption("Agent spend, gate decisions and budget headroom for project homeiq")

    client = AgentForgeClient(base_url=settings.agentforge_url, api_key=settings.agentforge_api_key)
    if not run_async_safe(client.health_check()):
        st.error(
            f"AgentForge unreachable at {settings.agentforge_url}. "
            "Check AGENTFORGE_URL and AGENTFORGE_API_KEY — this page shows no data rather "
            "than reporting an empty-but-healthy project."
        )
        return

    budgets = load_agent_budgets(repo_root())
    stats = run_async_safe(client.get_per_agent_stats(budgets)) or []
    _render_spend(run_async_safe(client.get_spend()))
    _render_agents(stats)
    _render_gates(run_async_safe(client.get_gate_decisions()) or [])
    _render_budgets(budgets, stats)
