"""
Service Performance Monitoring Dashboard Page
Monitor service health and performance metrics
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

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
    Display service performance monitoring dashboard.
    
    Shows service health, latency metrics, error rates, and dependencies.
    """
    st.header("⚡ Service Performance Monitoring")
    st.markdown("Monitor service health across all 30+ microservices")

    # Sidebar filters
    with st.sidebar:
        st.subheader("Filters")

        # Time range
        time_range = st.selectbox(
            "Time Range",
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

        # Service selection
        try:
            services = run_async_safe(_get_services(), timeout=30.0)
            service_names = [s.name for s in services] if services else []
        except Exception as e:
            st.error(f"Failed to load services: {e}")
            service_names = []
        selected_services = st.multiselect("Services", service_names, default=service_names[:10] if service_names else [])

    # Query performance data
    if st.button("📊 Load Performance Data", type="primary"):
        with st.spinner("Loading performance data..."):
            try:
                # Get traces for all services
                all_traces = []
                services_to_query = selected_services if selected_services else service_names
                for service in services_to_query:
                    traces = run_async_safe(
                        st.session_state.jaeger_client.get_traces(
                            service=service,
                            start_time=start_time,
                            end_time=end_time,
                            limit=100,
                        ),
                        timeout=60.0,
                    )
                    all_traces.extend(traces)

                if all_traces:
                    st.session_state.performance_traces = all_traces
                    st.success(f"Loaded {len(all_traces)} traces")
                else:
                    st.warning("No traces found")
                    if "performance_traces" in st.session_state:
                        del st.session_state.performance_traces
            except Exception as e:
                st.error(f"Failed to load performance data: {e}")
                if "performance_traces" in st.session_state:
                    del st.session_state.performance_traces

    # Display performance metrics
    if "performance_traces" in st.session_state and st.session_state.performance_traces:
        traces = st.session_state.performance_traces

        # Calculate service health metrics
        service_metrics = _calculate_service_metrics(traces)

        # Service health overview
        st.subheader("Service Health Overview")
        health_df = _create_health_dataframe(service_metrics)
        st.dataframe(health_df, use_container_width=True, height=400)

        # Latency percentiles
        st.subheader("Latency Percentiles")
        latency_df = _create_latency_dataframe(service_metrics)
        if not latency_df.empty:
            fig = go.Figure()
            for percentile in ["p50", "p95", "p99"]:
                if percentile in latency_df.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=latency_df["Service"],
                            y=latency_df[percentile],
                            mode="lines+markers",
                            name=percentile,
                        )
                    )
            fig.update_layout(
                title="Latency Percentiles by Service",
                xaxis_title="Service",
                yaxis_title="Latency (ms)",
                height=400,
            )
            st.plotly_chart(fig, use_container_width=True)

        # Error rates
        st.subheader("Error Rates")
        error_df = _create_error_dataframe(service_metrics)
        if not error_df.empty:
            fig = px.bar(
                error_df,
                x="Service",
                y="Error Rate (%)",
                title="Error Rate by Service",
                color="Error Rate (%)",
                color_continuous_scale="Reds",
            )
            st.plotly_chart(fig, use_container_width=True)

        # Service dependency health
        st.subheader("Service Dependency Health")
        try:
            deps = run_async_safe(
                st.session_state.jaeger_client.get_dependencies(
                    start_time=start_time,
                    end_time=end_time,
                ),
                timeout=30.0,
            )
        except Exception as e:
            st.error(f"Failed to load dependencies: {e}")
            deps = []
        if deps:
            deps_df = pd.DataFrame([{"Parent": d.parent, "Child": d.child, "Call Count": d.callCount} for d in deps])
            st.dataframe(deps_df, use_container_width=True)
    else:
        st.info("👆 Click 'Load Performance Data' to analyze service performance")


async def _get_services() -> List[Service]:
    """
    Get list of services from Jaeger.
    
    Returns:
        List of Service objects
    """
    client: JaegerClient = st.session_state.jaeger_client
    return await client.get_services()


def _calculate_service_metrics(traces: List[Trace]) -> Dict[str, Dict]:
    """Calculate performance metrics for each service."""
    service_metrics: Dict[str, Dict] = {}

    for trace in traces:
        for span in trace.spans:
            service_name = trace.processes.get(span.processID, {}).get("serviceName", "unknown")

            if service_name not in service_metrics:
                service_metrics[service_name] = {
                    "durations": [],
                    "error_count": 0,
                    "total_count": 0,
                }

            duration_ms = span.duration / 1000  # Convert to milliseconds
            service_metrics[service_name]["durations"].append(duration_ms)
            service_metrics[service_name]["total_count"] += 1

            # Check for errors
            for tag in span.tags:
                if tag.get("key") == "error" and tag.get("value"):
                    service_metrics[service_name]["error_count"] += 1
                    break

    # Calculate percentiles and error rates
    for service_name, metrics in service_metrics.items():
        durations = sorted(metrics["durations"])
        if durations:
            metrics["p50"] = durations[int(len(durations) * 0.50)]
            metrics["p95"] = durations[int(len(durations) * 0.95)] if len(durations) > 1 else durations[0]
            metrics["p99"] = durations[int(len(durations) * 0.99)] if len(durations) > 1 else durations[0]
            metrics["avg"] = sum(durations) / len(durations)
            metrics["min"] = min(durations)
            metrics["max"] = max(durations)
        else:
            metrics["p50"] = metrics["p95"] = metrics["p99"] = metrics["avg"] = metrics["min"] = metrics["max"] = 0

        metrics["error_rate"] = (
            (metrics["error_count"] / metrics["total_count"] * 100) if metrics["total_count"] > 0 else 0
        )

    return service_metrics


def _create_health_dataframe(service_metrics: Dict[str, Dict[str, float]]) -> pd.DataFrame:
    """
    Create service health DataFrame.
    
    Args:
        service_metrics: Dictionary of service metrics
        
    Returns:
        DataFrame with service health information
    """
    data = []
    for service_name, metrics in service_metrics.items():
        # Determine health status
        if metrics["error_rate"] > 10:
            health_status = "🔴 Critical"
        elif metrics["error_rate"] > 5:
            health_status = "🟡 Warning"
        elif metrics["p95"] > 1000:  # p95 > 1 second
            health_status = "🟡 Warning"
        else:
            health_status = "🟢 Healthy"

        data.append(
            {
                "Service": service_name,
                "Status": health_status,
                "Total Requests": metrics["total_count"],
                "Errors": metrics["error_count"],
                "Error Rate (%)": f"{metrics['error_rate']:.2f}",
                "Avg Latency (ms)": f"{metrics['avg']:.2f}",
                "P95 Latency (ms)": f"{metrics['p95']:.2f}",
            }
        )

    return pd.DataFrame(data).sort_values("Service")


def _create_latency_dataframe(service_metrics: Dict[str, Dict[str, float]]) -> pd.DataFrame:
    """
    Create latency percentiles DataFrame.
    
    Args:
        service_metrics: Dictionary of service metrics
        
    Returns:
        DataFrame with latency percentile data
    """
    data = []
    for service_name, metrics in service_metrics.items():
        data.append(
            {
                "Service": service_name,
                "p50": metrics["p50"],
                "p95": metrics["p95"],
                "p99": metrics["p99"],
            }
        )

    return pd.DataFrame(data).sort_values("Service")


def _create_error_dataframe(service_metrics: Dict[str, Dict[str, float]]) -> pd.DataFrame:
    """
    Create error rate DataFrame.
    
    Args:
        service_metrics: Dictionary of service metrics
        
    Returns:
        DataFrame with error rate information
    """
    data = []
    for service_name, metrics in service_metrics.items():
        data.append(
            {
                "Service": service_name,
                "Error Rate (%)": metrics["error_rate"],
                "Error Count": metrics["error_count"],
                "Total Requests": metrics["total_count"],
            }
        )

    return pd.DataFrame(data).sort_values("Service", ascending=False)
