"""
Data Generation Configuration

Configuration for data generation manager.
"""

import logging
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class DataGenerationConfig(BaseSettings):
    """
    Configuration for data generation manager.
    
    Manages generation parameters, caching, and validation settings.
    """

    model_config = {
        "env_prefix": "SIMULATION_DATA_GEN_",
        "case_sensitive": False,
    }

    # Generation parameters
    default_home_count: int = Field(
        default=50,
        description="Default number of homes to generate"
    )
    default_event_days: int = Field(
        default=90,
        description="Default number of days of events per home"
    )
    max_parallel_generations: int = Field(
        default=5,
        description="Maximum parallel home generations"
    )

    # Home type distribution (can be overridden)
    home_types: list[str] = Field(
        default_factory=lambda: [
            "single_family_house",
            "apartment",
            "condo",
            "townhouse",
            "cottage",
            "studio",
            "multi_story",
            "ranch_house"
        ],
        description="Home types to generate"
    )

    # Caching
    cache_enabled: bool = Field(
        default=True,
        description="Enable generation cache"
    )
    cache_directory: Path = Field(
        default=Path("simulation/data/cache"),
        description="Cache directory for generated homes"
    )
    cache_ttl_hours: int = Field(
        default=24,
        description="Cache TTL in hours"
    )

    # Validation
    validate_generated_data: bool = Field(
        default=True,
        description="Validate generated data quality"
    )
    min_events_per_home: int = Field(
        default=100,
        description="Minimum events per home for validation"
    )
    min_devices_per_home: int = Field(
        default=10,
        description="Minimum devices per home for validation"
    )

    def __init__(self, **kwargs: Any) -> None:
        """Initialize configuration."""
        super().__init__(**kwargs)
        # Ensure cache directory exists
        if self.cache_enabled:
            self.cache_directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Cache directory: {self.cache_directory}")

