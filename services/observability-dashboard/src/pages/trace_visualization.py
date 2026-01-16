"""
Trace Visualization Dashboard Page
Visualize distributed traces across HomeIQ services
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from services.jaeger_client import JaegerClient, Service, Trace
from utils.async_helpers import run_async_safe

# Initialize Jaeger client in session state
if "jaeger_client" not in st.session_state:
    st.session_state.jaeger_client = JaegerClient()


def show() -> None:
    """
    Display trace visualization dashboard.
    
    Shows distributed traces with filtering, visualization, and detailed inspection.
    """
    st.header("🔍 Trace Visualization")
    st.markdown("Visualize distributed traces across 30+ HomeIQ services")

    # Sidebar filters
    with st.sidebar:
        st.subheader("Filters")

        # Service filter
        try:
            services = _get_services_safe()
            service_names = [s.name for s in services] if services else []
        except Exception as e:
            st.error(f"Failed to load services: {e}")
            service_names = []
        selected_service = st.selectbox(
            "Service",
            ["All"] + service_names,
            index=0,
        )

        # Time range filter
        st.subheader("Time Range")
        time_range = st.selectbox(
            "Range",
            ["Last 15 minutes", "Last hour", "Last 6 hours", "Last 24 hours", "Custom"],
            index=1,
        )

        if time_range == "Custom":
            start_time = st.datetime_input("Start Time", value=datetime.utcnow() - timedelta(hours=1))
            end_time = st.datetime_input("End Time", value=datetime.utcnow())
        else:
            end_time = datetime.utcnow()
            if time_range == "Last 15 minutes":
                start_time = end_time - timedelta(minutes=15)
            elif time_range == "Last hour":
                start_time = end_time - timedelta(hours=1)
            elif time_range == "Last 6 hours":
                start_time = end_time - timedelta(hours=6)
            else:  # Last 24 hours
                start_time = end_time - timedelta(hours=24)

        # Limit
        limit = st.slider("Max Traces", 10, 500, 100)

        # Search
        trace_id_search = st.text_input("Search Trace ID")
        correlation_id_search = st.text_input("Search Correlation ID")

    # Query traces
    if st.button("🔍 Query Traces", type="primary"):
        with st.spinner("Querying traces..."):
            try:
                traces = _query_traces_safe(
                    service=selected_service if selected_service != "All" else None,
                    start_time=start_time,
                    end_time=end_time,
                    limit=limit,
                    trace_id=trace_id_search if trace_id_search else None,
                )

                if traces:
                    st.session_state.traces = traces
                    st.success(f"Found {len(traces)} traces")
                else:
                    st.warning("No traces found")
                    if "traces" in st.session_state:
                        del st.session_state.traces
            except Exception as e:
                st.error(f"Failed to query traces: {e}")
                if "traces" in st.session_state:
                    del st.session_state.traces

    # Display traces
    if "traces" in st.session_state and st.session_state.traces:
        traces = st.session_state.traces

        # Summary statistics
        st.subheader("Summary Statistics")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Traces", len(traces))
        with col2:
            total_spans = sum(len(trace.spans) for trace in traces)
            st.metric("Total Spans", total_spans)
        with col3:
            avg_duration = sum(
                sum(span.duration for span in trace.spans) / len(trace.spans) if trace.spans else 0
                for trace in traces
            ) / len(traces) if traces else 0
            st.metric("Avg Duration (μs)", f"{avg_duration:,.0f}")
        with col4:
            error_traces = sum(1 for trace in traces if _has_errors(trace))
            st.metric("Error Traces", error_traces)

        # Trace timeline visualization
        st.subheader("Trace Timeline")
        timeline_fig = _create_timeline_chart(traces)
        st.plotly_chart(timeline_fig, use_container_width=True)

        # Service dependency graph
        st.subheader("Service Dependency Graph")
        deps_fig = _create_dependency_graph(traces)
        st.plotly_chart(deps_fig, use_container_width=True)

        # Trace list
        st.subheader("Trace List")
        trace_df = _create_trace_dataframe(traces)
        st.dataframe(trace_df, use_container_width=True, height=400)

        # Trace details
        if len(traces) > 0:
            st.subheader("Trace Details")
            selected_trace_idx = st.selectbox(
                "Select Trace",
                range(len(traces)),
                format_func=lambda i: f"Trace {traces[i].traceID[:16]}... ({len(traces[i].spans)} spans)",
            )

            if selected_trace_idx is not None and 0 <= selected_trace_idx < len(traces):
                trace = traces[selected_trace_idx]
                _show_trace_details(trace)
    else:
        st.info("👆 Click 'Query Traces' to load traces")


def _get_services_safe() -> List[Service]:
    """
    Get services from Jaeger safely handling async operations.
    
    Returns:
        List of services from Jaeger
    """
    try:
        return run_async_safe(_get_services(), timeout=30.0)
    except Exception as e:
        st.error(f"Error getting services: {e}")
        return []


async def _get_services() -> List[Service]:
    """
    Get list of services from Jaeger.
    
    Returns:
        List of Service objects
    """
    client: JaegerClient = st.session_state.jaeger_client
    return await client.get_services()


def _query_traces_safe(
    service: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 100,
    trace_id: Optional[str] = None,
) -> List[Trace]:
    """
    Query traces from Jaeger safely handling async operations.
    
    Args:
        service: Optional service name filter
        start_time: Optional start time for query
        end_time: Optional end time for query
        limit: Maximum number of traces to return
        trace_id: Optional trace ID to get specific trace
        
    Returns:
        List of Trace objects
    """
    try:
        return run_async_safe(
            _query_traces(service, start_time, end_time, limit, trace_id),
            timeout=60.0,
        )
    except Exception as e:
        st.error(f"Error querying traces: {e}")
        return []


async def _query_traces(
    service: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 100,
    trace_id: Optional[str] = None,
) -> List[Trace]:
    """
    Query traces from Jaeger.
    
    Args:
        service: Optional service name filter
        start_time: Optional start time for query
        end_time: Optional end time for query
        limit: Maximum number of traces to return
        trace_id: Optional trace ID to get specific trace
        
    Returns:
        List of Trace objects
    """
    client: JaegerClient = st.session_state.jaeger_client

    if trace_id:
        # Get specific trace
        trace = await client.get_trace(trace_id)
        return [trace] if trace else []
    else:
        # Query traces
        return await client.get_traces(
            service=service,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )


def _has_errors(trace: Trace) -> bool:
    """Check if trace has errors."""
    for span in trace.spans:
        for tag in span.tags:
            if tag.get("key") == "error" and tag.get("value"):
                return True
    return False


def _create_timeline_chart(traces: List[Trace]) -> go.Figure:
    """Create timeline visualization of traces."""
    data = []
    for trace in traces:
        for span in trace.spans:
            service_name = trace.processes.get(span.processID, {}).get("serviceName", "unknown")
            start_ms = span.startTime / 1000  # Convert to milliseconds
            duration_ms = span.duration / 1000

            data.append(
                {
                    "Trace ID": trace.traceID[:16],
                    "Service": service_name,
                    "Operation": span.operationName,
                    "Start (ms)": start_ms,
                    "Duration (ms)": duration_ms,
                    "Has Error": _has_errors(trace),
                }
            )

    if not data:
        # Return empty figure
        fig = go.Figure()
        fig.add_annotation(text="No trace data available", showarrow=False)
        return fig

    df = pd.DataFrame(data)

    # Create Gantt chart
    fig = go.Figure()

    for service in df["Service"].unique():
        service_df = df[df["Service"] == service]
        fig.add_trace(
            go.Scatter(
                x=service_df["Start (ms)"],
                y=service_df["Operation"],
                mode="markers",
                name=service,
                marker=dict(
                    size=service_df["Duration (ms)"],
                    sizemode="diameter",
                    sizeref=2 * max(service_df["Duration (ms)"]) / (20**2),
                    color=service_df["Has Error"].map({True: "red", False: "blue"}),
                ),
            )
        )

    fig.update_layout(
        title="Trace Timeline",
        xaxis_title="Time (ms)",
        yaxis_title="Operation",
        height=600,
    )

    return fig


def _create_dependency_graph(traces: List[Trace]) -> go.Figure:
    """Create service dependency graph."""
    # Extract service dependencies from traces
    dependencies = {}
    for trace in traces:
        for span in trace.spans:
            service_name = trace.processes.get(span.processID, {}).get("serviceName", "unknown")
            # Look for parent references
            for ref in span.references:
                if ref.get("refType") == "CHILD_OF":
                    parent_span_id = ref.get("spanID")
                    # Find parent span
                    for parent_span in trace.spans:
                        if parent_span.spanID == parent_span_id:
                            parent_service = trace.processes.get(parent_span.processID, {}).get(
                                "serviceName", "unknown"
                            )
                            key = (parent_service, service_name)
                            dependencies[key] = dependencies.get(key, 0) + 1

    if not dependencies:
        # Return empty figure
        fig = go.Figure()
        fig.add_annotation(text="No dependency data available", showarrow=False)
        return fig

    # Create network graph
    nodes = set()
    edges = []
    for (parent, child), count in dependencies.items():
        nodes.add(parent)
        nodes.add(child)
        edges.append((parent, child, count))

    # Create Sankey diagram
    node_labels = list(nodes)
    node_indices = {node: i for i, node in enumerate(node_labels)}

    source = []
    target = []
    value = []
    for parent, child, count in edges:
        source.append(node_indices[parent])
        target.append(node_indices[child])
        value.append(count)

    fig = go.Figure(
        data=[
            go.Sankey(
                node=dict(label=node_labels),
                link=dict(source=source, target=target, value=value),
            )
        ]
    )

    fig.update_layout(title="Service Dependencies", height=600)

    return fig


def _create_trace_dataframe(traces: List[Trace]) -> pd.DataFrame:
    """Create DataFrame from traces."""
    data = []
    for trace in traces:
        service_names = [
            trace.processes.get(span.processID, {}).get("serviceName", "unknown")
            for span in trace.spans
        ]
        unique_services = list(set(service_names))
        total_duration = sum(span.duration for span in trace.spans)

        data.append(
            {
                "Trace ID": trace.traceID[:16] + "...",
                "Full Trace ID": trace.traceID,
                "Services": ", ".join(unique_services),
                "Span Count": len(trace.spans),
                "Total Duration (μs)": total_duration,
                "Has Error": _has_errors(trace),
            }
        )

    return pd.DataFrame(data)


def _show_trace_details(trace: Trace) -> None:
    """
    Show detailed trace information.
    
    Args:
        trace: Trace object to display
    """
    st.json(trace.model_dump())
