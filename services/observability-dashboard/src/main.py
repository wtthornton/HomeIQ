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
import sys
from pathlib import Path

import streamlit as st

# Add shared directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "shared"))

# Configure Streamlit page
st.set_page_config(
    page_title="HomeIQ Observability Dashboard",
    page_icon="📊",
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
    st.title("📊 HomeIQ Observability Dashboard")
    st.markdown("**Internal Admin Tool** - OpenTelemetry observability and automation debugging")

    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Select Dashboard",
        [
            "🏠 Home",
            "🔍 Trace Visualization",
            "🤖 Automation Debugging",
            "⚡ Service Performance",
            "📡 Real-Time Monitoring",
        ],
    )

    # Route to appropriate page
    if page == "🏠 Home":
        show_home()
    elif page == "🔍 Trace Visualization":
        from pages import trace_visualization
        trace_visualization.show()
    elif page == "🤖 Automation Debugging":
        from pages import automation_debugging
        automation_debugging.show()
    elif page == "⚡ Service Performance":
        from pages import service_performance
        service_performance.show()
    elif page == "📡 Real-Time Monitoring":
        from pages import real_time_monitoring
        real_time_monitoring.show()


def show_home() -> None:
    """
    Display home page with overview.
    
    Shows welcome message and configuration status.
    """
    st.header("Welcome to HomeIQ Observability Dashboard")
    st.markdown(
        """
        This dashboard provides internal/admin tools for observability, automation debugging,
        and operational excellence using OpenTelemetry.
        
        **Available Dashboards:**
        - **Trace Visualization**: Visualize distributed traces across 30+ services
        - **Automation Debugging**: Debug automation execution with end-to-end traces
        - **Service Performance**: Monitor service health and performance metrics
        - **Real-Time Monitoring**: Live observability with auto-refresh
        
        **Note:** This is an internal tool only. Customer-facing dashboards remain in React.
        """
    )

    # Configuration status
    st.subheader("Configuration Status")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Jaeger:**")
        st.code(f"URL: {st.session_state.config['jaeger_url']}")
        st.code(f"API: {st.session_state.config['jaeger_api_url']}")

    with col2:
        st.markdown("**HomeIQ APIs:**")
        st.code(f"Data API: {st.session_state.config['data_api_url']}")
        st.code(f"Admin API: {st.session_state.config['admin_api_url']}")


if __name__ == "__main__":
    main()
