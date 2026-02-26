"""
Observability Dashboard Service
Streamlit-based internal admin tool for OpenTelemetry observability

This service provides internal/admin dashboards for:
- Distributed trace visualization
- Automation debugging
- Service performance monitoring
- Real-time observability
"""

import os

import streamlit as st

# Configure Streamlit page
st.set_page_config(
    page_title="HomeIQ Ops",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Environment variables
JAEGER_URL = os.getenv("JAEGER_URL", "http://jaeger:16686")
JAEGER_API_URL = os.getenv("JAEGER_API_URL", "http://jaeger:16686/api")
OTLP_ENDPOINT = os.getenv("OTLP_ENDPOINT", "http://jaeger:4317")
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
DATA_API_URL = os.getenv("DATA_API_URL", "http://data-api:8006")
ADMIN_API_URL = os.getenv("ADMIN_API_URL", "http://admin-api:8004")

# Store configuration in session state
if "config" not in st.session_state:
    st.session_state.config = {
        "jaeger_url": JAEGER_URL,
        "jaeger_api_url": JAEGER_API_URL,
        "otlp_endpoint": OTLP_ENDPOINT,
        "influxdb_url": INFLUXDB_URL,
        "data_api_url": DATA_API_URL,
        "admin_api_url": ADMIN_API_URL,
    }


def main() -> None:
    """
    Main Streamlit application entry point.

    Initializes the dashboard and routes to appropriate pages.
    """
    st.title("🔧 HomeIQ Ops")
    st.markdown("**Internal Observability & Debugging**")

    # Sidebar connections info
    with st.sidebar.expander("Connections", expanded=False):
        st.code(f"Jaeger: {st.session_state.config['jaeger_url']}")
        st.code(f"Data API: {st.session_state.config['data_api_url']}")
        st.code(f"Admin API: {st.session_state.config['admin_api_url']}")

    # Cross-app switcher (FR-5.1)
    st.sidebar.markdown("---")
    cols = st.sidebar.columns(3)
    with cols[0]:
        automation_url = os.getenv("AI_AUTOMATION_UI_URL", "http://localhost:3001")
        st.markdown(f"[HomeIQ]({automation_url})")
    with cols[1]:
        health_url = os.getenv("HEALTH_DASHBOARD_URL", "http://localhost:3000")
        st.markdown(f"[Health]({health_url})")
    with cols[2]:
        st.markdown("**Ops**")
    st.sidebar.markdown("---")

    # Sidebar navigation
    page = st.sidebar.radio(
        "Dashboard",
        [
            "🔍 Traces",
            "⚡ Performance",
            "📡 Live",
        ],
    )

    # Route to appropriate page
    if page == "🔍 Traces":
        from pages import trace_visualization
        trace_visualization.show()
    elif page == "⚡ Performance":
        from pages import service_performance
        service_performance.show()
    elif page == "📡 Live":
        from pages import real_time_monitoring
        real_time_monitoring.show()


if __name__ == "__main__":
    main()
