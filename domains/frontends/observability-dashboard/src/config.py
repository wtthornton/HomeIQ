"""Configuration settings for Observability Dashboard.

Uses BaseServiceSettings from homeiq-data for consistent environment
variable handling.  The observability dashboard is a Streamlit app, so
ServiceLifespan / create_app do not apply.  Only the settings layer is
migrated to replace bare ``os.getenv()`` calls.
"""

from homeiq_data import BaseServiceSettings
from pydantic import Field


class Settings(BaseServiceSettings):
    """Application settings loaded from environment variables."""

    # Override base defaults
    service_port: int = 8501
    service_name: str = "observability-dashboard"

    # Jaeger
    jaeger_url: str = Field(
        default="http://jaeger:16686",
        description="Jaeger UI base URL",
    )
    jaeger_api_url: str = Field(
        default="http://jaeger:16686/api",
        description="Jaeger query API URL",
    )

    # Upstream HomeIQ APIs
    admin_api_url: str = Field(
        default="http://admin-api:8004",
        description="Admin API base URL",
    )

    # Cross-app switcher URLs
    ai_automation_ui_url: str = Field(
        default="http://localhost:3001",
        description="AI Automation UI URL for cross-app switcher",
    )
    health_dashboard_url: str = Field(
        default="http://localhost:3000",
        description="Health Dashboard URL for cross-app switcher",
    )


settings = Settings()
