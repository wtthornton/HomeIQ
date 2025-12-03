"""
Simulation Configuration Management

Configuration management using Pydantic Settings 2.x for simulation framework.
"""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SimulationConfig(BaseSettings):
    """
    Simulation framework configuration.
    
    Uses Pydantic Settings 2.x for configuration management with support for:
    - Environment variables
    - Configuration files
    - Type validation
    """

    model_config = SettingsConfigDict(
        env_prefix="SIMULATION_",
        env_file=".env.simulation",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Simulation mode
    mode: Literal["quick", "standard", "stress"] = Field(
        default="standard",
        description="Simulation mode: quick (fast, minimal), standard (balanced), stress (comprehensive)"
    )

    # Model configuration
    model_mode: Literal["pretrained", "train_during"] = Field(
        default="pretrained",
        description="Model loading mode: pretrained (fast, load from models/), train_during (comprehensive, train on simulation data)"
    )
    models_directory: Path = Field(
        default=Path("models"),
        description="Directory containing pre-trained models"
    )

    # Synthetic data configuration
    synthetic_data_directory: Path = Field(
        default=Path("simulation/data"),
        description="Directory containing synthetic home data"
    )
    synthetic_homes_count: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Number of synthetic homes to simulate"
    )

    # Results configuration
    results_directory: Path = Field(
        default=Path("simulation/results"),
        description="Directory for simulation results and reports"
    )

    # Performance configuration
    max_parallel_homes: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of homes to process in parallel"
    )
    max_parallel_queries: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of Ask AI queries to process in parallel"
    )

    # Validation configuration
    enable_prompt_validation: bool = Field(
        default=True,
        description="Enable prompt quality validation"
    )
    enable_yaml_validation: bool = Field(
        default=True,
        description="Enable YAML validation framework"
    )
    enable_ground_truth_comparison: bool = Field(
        default=True,
        description="Enable ground truth comparison with automation datasets"
    )

    # Metrics configuration
    collect_detailed_metrics: bool = Field(
        default=True,
        description="Collect detailed metrics for analysis"
    )

    # Logging configuration
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Logging level"
    )

    def get_synthetic_home_path(self, home_id: str) -> Path:
        """Get path to synthetic home data file."""
        return self.synthetic_data_directory / f"home_{home_id}.json"

    def get_results_path(self, filename: str) -> Path:
        """Get path to results file."""
        self.results_directory.mkdir(parents=True, exist_ok=True)
        return self.results_directory / filename

