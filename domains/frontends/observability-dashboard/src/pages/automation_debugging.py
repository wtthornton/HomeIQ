"""
Automation Debugging Dashboard Page
Debug automation execution with end-to-end traces
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from services.jaeger_client import JaegerClient, Trace
from utils.async_helpers import run_async_safe
from utils.trace_helpers import has_errors, trace_wall_clock_ms

# Initialize Jaeger client in session state
if "jaeger_client" not in st.session_state:
    st.session_state.jaeger_client = JaegerClient()


def show() -> None:
    """
    Display automation debugging dashboard.

    Shows automation execution traces with filtering and performance analysis.
    """
    st.header("🤖 Automation Debugging")
    st.markdown("Trace automation execution from trigger → validation → execution → confirmation")

    # Sidebar filters
    with st.sidebar:
        st.subheader("Filters")

        # Automation ID filter
        automation_id = st.text_input("Automation ID")

        # Home ID filter
        home_id = st.text_input("Home ID")

        # Correlation ID filter
        correlation_id = st.text_input("Correlation ID")

        # Time range
        st.subheader("Time Range")
        time_range = st.selectbox(
            "Range",
            ["Last hour", "Last 6 hours", "Last 24 hours", "Custom"],
            index=0,
        )

        if time_range == "Custom":
            start_time = st.datetime_input("Start Time", value=datetime.utcnow() - timedelta(hours=1))
            end_time = st.datetime_input("End Time", value=datetime.utcnow())
        else:
            end_time = datetime.utcnow()
            if time_range == "Last hour":
                start_time = end_time - timedelta(hours=1)
            elif time_range == "Last 6 hours":
                start_time = end_time - timedelta(hours=6)
            else:  # Last 24 hours
                start_time = end_time - timedelta(hours=24)

    # Query automation traces
    if st.button("🔍 Query Automation Traces", type="primary"):
        with st.spinner("Querying automation traces..."):
            try:
                traces = run_async_safe(
                    _query_automation_traces(
                        automation_id=automation_id if automation_id else None,
                        home_id=home_id if home_id else None,
                        correlation_id=correlation_id if correlation_id else None,
                        start_time=start_time,
                        end_time=end_time,
                    ),
                    timeout=60.0,
                )

                if traces:
                    st.session_state.automation_traces = traces
                    st.success(f"Found {len(traces)} automation traces")
                else:
                    st.warning("No automation traces found")
                    if "automation_traces" in st.session_state:
                        del st.session_state.automation_traces
            except Exception as e:
                st.error(f"Failed to query automation traces: {e}")
                if "automation_traces" in st.session_state:
                    del st.session_state.automation_traces

    # Display automation traces
    if "automation_traces" in st.session_state and st.session_state.automation_traces:
        traces = st.session_state.automation_traces

        # Summary statistics
        st.subheader("Automation Statistics")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Executions", len(traces))
        with col2:
            success_count = sum(1 for trace in traces if _is_automation_success(trace))
            st.metric("Successful", success_count)
        with col3:
            failure_count = len(traces) - success_count
            st.metric("Failed", failure_count)
        with col4:
            success_rate = (success_count / len(traces) * 100) if traces else 0
            st.metric("Success Rate", f"{success_rate:.1f}%")

        # Automation flow visualization
        st.subheader("Automation Flow")
        if len(traces) > 0:
            selected_trace_idx = st.selectbox(
                "Select Automation Execution",
                range(len(traces)),
                format_func=lambda i: f"Execution {i+1} - {traces[i].traceID[:16]}...",
            )

            if selected_trace_idx is not None:
                trace = traces[selected_trace_idx]
                _show_automation_flow(trace)

        # Automation performance metrics
        st.subheader("Performance Metrics")
        perf_df = _create_performance_dataframe(traces)
        if not perf_df.empty:
            st.dataframe(perf_df, use_container_width=True)

            # Performance chart
            fig = px.bar(
                perf_df,
                x="Execution",
                y="Duration (ms)",
                color="Status",
                title="Automation Execution Duration",
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("👆 Click 'Query Automation Traces' to load traces")


async def _query_automation_traces(
    automation_id: str | None = None,
    home_id: str | None = None,
    correlation_id: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> list[Trace]:
    """Query automation traces from Jaeger."""
    client = st.session_state.jaeger_client

    traces = await client.get_traces(
        service="ai-automation-service",
        start_time=start_time,
        end_time=end_time,
        limit=100,
    )

    # If no filters provided, return all traces
    if not automation_id and not home_id and not correlation_id:
        return traces

    # Filter by automation ID, home ID, or correlation ID
    filtered_traces = []
    for trace in traces:
        matched = False
        for span in trace.spans:
            for tag in span.tags:
                tag_key = tag.get("key", "")
                tag_value = tag.get("value", "")

                if (
                    (automation_id and tag_key == "automation_id" and tag_value == automation_id)
                    or (home_id and tag_key == "home_id" and tag_value == home_id)
                    or (correlation_id and tag_key == "correlation_id" and tag_value == correlation_id)
                ):
                    matched = True
                    break
            if matched:
                break
        if matched:
            filtered_traces.append(trace)

    return filtered_traces


def _is_automation_success(trace: Trace) -> bool:
    """Check if automation execution was successful."""
    if has_errors(trace):
        return False
    for span in trace.spans:
        for tag in span.tags:
            if tag.get("key") == "status" and tag.get("value") == "success":
                return True
    return True  # Assume success if no error tags


def _show_automation_flow(trace: Trace) -> None:
    """
    Show automation execution flow.

    Args:
        trace: Trace object to display
    """
    st.subheader("Execution Flow")

    # Extract automation steps from spans
    steps = []
    for span in sorted(trace.spans, key=lambda s: s.startTime):
        step_name = span.operationName
        duration_ms = span.duration / 1000

        # Extract "why" explanation from tags
        why_explanation = None
        for tag in span.tags:
            if tag.get("key") == "why" or tag.get("key") == "explanation":
                why_explanation = tag.get("value")
                break

        steps.append(
            {
                "Step": step_name,
                "Duration (ms)": duration_ms,
                "Why": why_explanation or "N/A",
            }
        )

    if steps:
        steps_df = pd.DataFrame(steps)
        st.dataframe(steps_df, use_container_width=True)

        # Horizontal bar chart for step durations
        fig = px.bar(
            steps_df,
            x="Duration (ms)",
            y="Step",
            orientation="h",
            title="Automation Execution Timeline",
        )
        st.plotly_chart(fig, use_container_width=True)

    # Show trace details
    with st.expander("Full Trace Details"):
        st.json(trace.model_dump())


def _create_performance_dataframe(traces: list[Trace]) -> pd.DataFrame:
    """Create performance metrics DataFrame."""
    data = []
    for i, trace in enumerate(traces):
        total_duration = trace_wall_clock_ms(trace)
        status = "Success" if _is_automation_success(trace) else "Failed"

        data.append(
            {
                "Execution": i + 1,
                "Trace ID": trace.traceID[:16] + "...",
                "Duration (ms)": total_duration,
                "Status": status,
                "Span Count": len(trace.spans),
            }
        )

    return pd.DataFrame(data)
