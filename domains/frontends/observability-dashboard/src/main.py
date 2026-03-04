"""
Observability Dashboard Service
Streamlit-based internal admin tool for OpenTelemetry observability

This service provides internal/admin dashboards for:
- Distributed trace visualization
- Automation debugging
- Service performance monitoring
- Real-time observability
"""

import streamlit as st

from config import settings

# Configure Streamlit page
st.set_page_config(
    page_title="HomeIQ Ops",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Store configuration in session state (from BaseServiceSettings)
if "config" not in st.session_state:
    st.session_state.config = {
        "jaeger_url": settings.jaeger_url,
        "jaeger_api_url": settings.jaeger_api_url,
        "data_api_url": settings.data_api_url,
        "admin_api_url": settings.admin_api_url,
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
        st.markdown(f"[HomeIQ]({settings.ai_automation_ui_url})")
    with cols[1]:
        st.markdown(f"[Health]({settings.health_dashboard_url})")
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
