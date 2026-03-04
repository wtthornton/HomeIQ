"""
Data Generation Framework

Synthetic data generation infrastructure for simulation framework.
"""

from .config import DataGenerationConfig
from .data_generation_manager import DataGenerationManager

__all__ = [
    "DataGenerationManager",
    "DataGenerationConfig",
]

