"""
Real-Time Observability Dashboard Page
Live trace streaming and real-time service health monitoring
"""

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from services.jaeger_client import JaegerClient, Trace
from utils.async_helpers import run_async_safe
from utils.trace_helpers import has_errors

# Initialize Jaeger client in session state
if "jaeger_client" not in st.session_state:
    st.session_state.jaeger_client = JaegerClient()

# Initialize real-time monitoring state
if "real_time_traces" not in st.session_state:
    st.session_state.real_time_traces = []
if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = False

# Map refresh interval options to timedelta for st.fragment
_REFRESH_OPTIONS = [5, 10, 30, 60]


def show() -> None:
    """
    Display real-time observability dashboard.

    Shows live trace streaming with auto-refresh and anomaly detection.
    """
    st.header("📡 Live")
    st.caption("Streaming traces and anomaly detection")

    # Controls
    col1, col2, col3 = st.columns(3)
    with col1:
        auto_refresh = st.checkbox("🔄 Auto-Refresh", value=st.session_state.auto_refresh)
        st.session_state.auto_refresh = auto_refresh

    with col2:
        refresh_interval = st.selectbox("Refresh Interval", _REFRESH_OPTIONS, index=1, format_func=lambda x: f"{x}s")

    with col3:
        if st.button("🛑 Stop Monitoring"):
            st.session_state.auto_refresh = False
            st.session_state.real_time_traces = []

    # Auto-refresh using st.fragment with run_every (non-blocking)
    if auto_refresh:
        _auto_refresh_fragment(refresh_interval)

    # Display real-time metrics
    if st.session_state.real_time_traces:
        traces = st.session_state.real_time_traces

        # Real-time statistics
        st.subheader("Real-Time Statistics")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Active Traces", len(traces))
        with col2:
            error_traces = sum(1 for trace in traces if has_errors(trace))
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
            st.metric("Last Update", datetime.now(UTC).strftime("%H:%M:%S"))

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


def _auto_refresh_fragment(refresh_interval: int) -> None:
    """Non-blocking auto-refresh using st.fragment with run_every."""

    @st.fragment(run_every=timedelta(seconds=refresh_interval))
    def _poll_traces() -> None:
        try:
            client: JaegerClient = st.session_state.jaeger_client
            traces = run_async_safe(
                _get_latest_traces(client, limit=50, lookback_minutes=5),
                timeout=30.0,
            )
        except Exception as e:
            st.error(f"Failed to load traces: {e}")
            return

        if traces:
            existing_ids = {t.traceID for t in st.session_state.real_time_traces}
            new_traces = [t for t in traces if t.traceID not in existing_ids]
            st.session_state.real_time_traces = (new_traces + st.session_state.real_time_traces)[:100]

            if new_traces:
                st.success(f"Received {len(new_traces)} new traces")

    _poll_traces()


async def _get_latest_traces(
    client: JaegerClient,
    limit: int = 50,
    lookback_minutes: int = 5,
) -> list[Trace]:
    """Get latest traces from Jaeger."""
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(minutes=lookback_minutes)

    return await client.get_traces(
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )


def _detect_anomalies(traces: list[Trace]) -> list[dict[str, str]]:
    """Detect anomalies in traces (high latency, errors). One entry per trace per type."""
    anomalies = []

    for trace in traces:
        # High latency: report per-span (each slow span is a distinct anomaly)
        for span in trace.spans:
            duration_ms = span.duration / 1000
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

        # Error: one entry per trace (de-duplicated, not per-span)
        if has_errors(trace):
            trace_duration = _trace_wall_clock_ms(trace)
            anomalies.append(
                {
                    "Type": "Error",
                    "Trace ID": trace.traceID[:16] + "...",
                    "Service": ", ".join(
                        {trace.processes.get(s.processID, {}).get("serviceName", "unknown") for s in trace.spans}
                    ),
                    "Operation": trace.spans[0].operationName if trace.spans else "unknown",
                    "Latency (ms)": f"{trace_duration:.2f}",
                }
            )

    return anomalies


def _trace_wall_clock_ms(trace: Trace) -> float:
    """Calculate wall-clock duration of a trace: max(start+duration) - min(start)."""
    if not trace.spans:
        return 0.0
    start = min(span.startTime for span in trace.spans)
    end = max(span.startTime + span.duration for span in trace.spans)
    return (end - start) / 1000  # microseconds to ms


def _create_realtime_dataframe(traces: list[Trace]) -> pd.DataFrame:
    """Create real-time trace DataFrame."""
    data = []
    for trace in traces:
        service_names = [
            trace.processes.get(span.processID, {}).get("serviceName", "unknown") for span in trace.spans
        ]
        unique_services = list(set(service_names))
        total_duration = _trace_wall_clock_ms(trace)

        data.append(
            {
                "Time": datetime.now(UTC).strftime("%H:%M:%S"),
                "Trace ID": trace.traceID[:16] + "...",
                "Services": ", ".join(unique_services),
                "Duration (ms)": f"{total_duration:.2f}",
                "Status": "Error" if has_errors(trace) else "OK",
            }
        )

    return pd.DataFrame(data)


def _calculate_service_health(traces: list[Trace]) -> list[dict[str, float]]:
    """Calculate real-time service health scores."""
    service_metrics: dict[str, dict] = {}

    for trace in traces:
        trace_has_error = has_errors(trace)
        for span in trace.spans:
            service_name = trace.processes.get(span.processID, {}).get("serviceName", "unknown")

            if service_name not in service_metrics:
                service_metrics[service_name] = {"errors": 0, "total": 0, "latencies": []}

            service_metrics[service_name]["total"] += 1
            service_metrics[service_name]["latencies"].append(span.duration / 1000)

            if trace_has_error:
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
