"""
Real-Time Observability Dashboard Page
Live trace streaming and real-time service health monitoring
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

import pandas as pd
import plotly.express as px
import streamlit as st

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from services.jaeger_client import JaegerClient, Trace
from utils.async_helpers import run_async_safe

# Initialize Jaeger client in session state
if "jaeger_client" not in st.session_state:
    st.session_state.jaeger_client = JaegerClient()

# Initialize real-time monitoring state
if "real_time_traces" not in st.session_state:
    st.session_state.real_time_traces = []
if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = False


def show() -> None:
    """
    Display real-time observability dashboard.
    
    Shows live trace streaming with auto-refresh and anomaly detection.
    """
    st.header("📡 Real-Time Observability")
    st.markdown("Live trace streaming and real-time service health monitoring")

    # Controls
    col1, col2, col3 = st.columns(3)
    with col1:
        auto_refresh = st.checkbox("🔄 Auto-Refresh", value=st.session_state.auto_refresh)
        st.session_state.auto_refresh = auto_refresh

    with col2:
        refresh_interval = st.selectbox("Refresh Interval", [5, 10, 30, 60], index=1, format_func=lambda x: f"{x}s")

    with col3:
        if st.button("🛑 Stop Monitoring"):
            st.session_state.auto_refresh = False
            st.session_state.real_time_traces = []

    # Auto-refresh logic
    if auto_refresh:
        # Query latest traces
        with st.spinner("Loading latest traces..."):
            try:
                traces = run_async_safe(
                    _get_latest_traces(
                        limit=50,
                        lookback_minutes=5,
                    ),
                    timeout=30.0,
                )
            except Exception as e:
                st.error(f"Failed to load traces: {e}")
                traces = []

            if traces:
                # Add new traces to state
                existing_ids = {t.traceID for t in st.session_state.real_time_traces}
                new_traces = [t for t in traces if t.traceID not in existing_ids]
                st.session_state.real_time_traces = (new_traces + st.session_state.real_time_traces)[:100]

                if new_traces:
                    st.success(f"📥 Received {len(new_traces)} new traces")

        # Auto-refresh using streamlit's rerun
        # Note: Streamlit will automatically refresh based on the interval
        # We use st.rerun() to trigger refresh, but avoid blocking with sleep
        if auto_refresh:
            import time
            time.sleep(refresh_interval)
            st.rerun()

    # Display real-time metrics
    if st.session_state.real_time_traces:
        traces = st.session_state.real_time_traces

        # Real-time statistics
        st.subheader("Real-Time Statistics")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Active Traces", len(traces))
        with col2:
            error_traces = sum(1 for trace in traces if _has_errors(trace))
            st.metric("Error Traces", error_traces, delta=f"{error_traces/len(traces)*100:.1f}%" if traces else "0%")
        with col3:
            avg_latency = (
                sum(sum(span.duration for span in trace.spans) / len(trace.spans) if trace.spans else 0 for trace in traces)
                / len(traces)
                / 1000
                if traces
                else 0
            )
            st.metric("Avg Latency (ms)", f"{avg_latency:.2f}")
        with col4:
            st.metric("Last Update", datetime.utcnow().strftime("%H:%M:%S"))

        # Anomaly detection
        st.subheader("🚨 Anomaly Detection")
        anomalies = _detect_anomalies(traces)
        if anomalies:
            st.warning(f"⚠️ {len(anomalies)} anomalies detected")
            anomaly_df = pd.DataFrame(anomalies)
            st.dataframe(anomaly_df, use_container_width=True)
        else:
            st.success("✅ No anomalies detected")

        # Live trace stream
        st.subheader("Live Trace Stream")
        trace_df = _create_realtime_dataframe(traces)
        st.dataframe(trace_df, use_container_width=True, height=400)

        # Service health status
        st.subheader("Service Health Status")
        service_health = _calculate_service_health(traces)
        health_df = pd.DataFrame(service_health)
        if not health_df.empty:
            fig = px.bar(
                health_df,
                x="Service",
                y="Health Score",
                color="Health Score",
                color_continuous_scale=["red", "yellow", "green"],
                title="Real-Time Service Health",
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("👆 Enable auto-refresh to start monitoring")


async def _get_latest_traces(limit: int = 50, lookback_minutes: int = 5) -> List[Trace]:
    """
    Get latest traces from Jaeger.
    
    Args:
        limit: Maximum number of traces to return
        lookback_minutes: Minutes to look back for traces
        
    Returns:
        List of Trace objects
    """
    client: JaegerClient = st.session_state.jaeger_client

    end_time = datetime.utcnow()
    start_time = end_time - timedelta(minutes=lookback_minutes)

    return await client.get_traces(
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


def _detect_anomalies(traces: List[Trace]) -> List[Dict[str, str]]:
    """
    Detect anomalies in traces (high latency, errors).
    
    Args:
        traces: List of traces to analyze
        
    Returns:
        List of anomaly dictionaries
    """
    anomalies = []

    for trace in traces:
        for span in trace.spans:
            duration_ms = span.duration / 1000

            # High latency anomaly (> 1 second)
            if duration_ms > 1000:
                anomalies.append(
                    {
                        "Type": "High Latency",
                        "Trace ID": trace.traceID[:16] + "...",
                        "Service": trace.processes.get(span.processID, {}).get("serviceName", "unknown"),
                        "Operation": span.operationName,
                        "Latency (ms)": f"{duration_ms:.2f}",
                    }
                )

            # Error anomaly
            if _has_errors(trace):
                anomalies.append(
                    {
                        "Type": "Error",
                        "Trace ID": trace.traceID[:16] + "...",
                        "Service": trace.processes.get(span.processID, {}).get("serviceName", "unknown"),
                        "Operation": span.operationName,
                        "Latency (ms)": f"{duration_ms:.2f}",
                    }
                )

    return anomalies


def _create_realtime_dataframe(traces: List[Trace]) -> pd.DataFrame:
    """
    Create real-time trace DataFrame.
    
    Args:
        traces: List of traces to convert to DataFrame
        
    Returns:
        DataFrame with trace information
    """
    data = []
    for trace in traces:
        service_names = [
            trace.processes.get(span.processID, {}).get("serviceName", "unknown") for span in trace.spans
        ]
        unique_services = list(set(service_names))
        total_duration = sum(span.duration for span in trace.spans) / 1000  # Convert to ms

        data.append(
            {
                "Time": datetime.utcnow().strftime("%H:%M:%S"),
                "Trace ID": trace.traceID[:16] + "...",
                "Services": ", ".join(unique_services),
                "Duration (ms)": f"{total_duration:.2f}",
                "Status": "🔴 Error" if _has_errors(trace) else "🟢 OK",
            }
        )

    return pd.DataFrame(data)


def _calculate_service_health(traces: List[Trace]) -> List[Dict[str, float]]:
    """
    Calculate real-time service health scores.
    
    Args:
        traces: List of traces to analyze
        
    Returns:
        List of service health dictionaries
    """
    service_metrics = {}

    for trace in traces:
        for span in trace.spans:
            service_name = trace.processes.get(span.processID, {}).get("serviceName", "unknown")

            if service_name not in service_metrics:
                service_metrics[service_name] = {"errors": 0, "total": 0, "latencies": []}

            service_metrics[service_name]["total"] += 1
            service_metrics[service_name]["latencies"].append(span.duration / 1000)

            if _has_errors(trace):
                service_metrics[service_name]["errors"] += 1

    # Calculate health scores (0-100)
    health_data = []
    for service_name, metrics in service_metrics.items():
        error_rate = (metrics["errors"] / metrics["total"] * 100) if metrics["total"] > 0 else 0
        avg_latency = sum(metrics["latencies"]) / len(metrics["latencies"]) if metrics["latencies"] else 0

        # Health score: 100 - (error_rate * 2) - (latency_penalty)
        latency_penalty = min(avg_latency / 10, 30)  # Max 30 point penalty
        health_score = max(0, 100 - (error_rate * 2) - latency_penalty)

        health_data.append(
            {
                "Service": service_name,
                "Health Score": round(health_score, 1),
                "Error Rate (%)": round(error_rate, 2),
                "Avg Latency (ms)": round(avg_latency, 2),
            }
        )

    return health_data
