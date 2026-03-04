"""Configuration settings for HA Simulator Service.

Uses BaseServiceSettings from homeiq-data for consistent environment
variable handling across all HomeIQ services.  The HA simulator is an
aiohttp WebSocket server (not FastAPI), so only the settings layer is
migrated -- ServiceLifespan/create_app do not apply here.
"""

from homeiq_data import BaseServiceSettings
from pydantic import Field


class Settings(BaseServiceSettings):
    """Application settings loaded from environment variables."""

    # Override base defaults
    service_port: int = 8123
    service_name: str = "ha-simulator"

    # Simulator identity
    simulator_name: str = Field(
        default="HA Development Simulator",
        description="Human-readable simulator name",
    )
    ha_version: str = Field(
        default="2025.10.1",
        description="Simulated Home Assistant version string",
    )

    # Authentication
    auth_enabled: bool = Field(default=True, description="Enable WebSocket authentication")
    auth_token: str = Field(
        default="dev_simulator_token",
        description="Expected bearer / access token for WS auth",
    )

    # Data patterns
    log_file_path: str = Field(
        default="data/ha_events.log",
        description="Path to HA event log used for pattern analysis",
    )

    # Logging (override from env)
    log_level: str = Field(default="INFO", description="Logging level")


settings = Settings()
