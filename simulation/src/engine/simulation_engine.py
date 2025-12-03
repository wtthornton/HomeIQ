"""
Simulation Engine Core

Main orchestrator for simulation framework with dependency injection and
workflow orchestration.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any

from .config import SimulationConfig
from .dependency_injection import DependencyContainer

logger = logging.getLogger(__name__)


class SimulationEngine:
    """
    Core simulation engine orchestrator.
    
    Manages:
    - Configuration
    - Dependency injection
    - Workflow orchestration
    - Results aggregation
    """

    def __init__(self, config: SimulationConfig | None = None):
        """
        Initialize simulation engine.
        
        Args:
            config: Simulation configuration (default: load from environment)
        """
        self.config = config or SimulationConfig()
        self.container = DependencyContainer()
        self._initialized = False

        # Setup logging
        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        logger.info(f"SimulationEngine initialized (mode={self.config.mode})")

    async def initialize(self) -> None:
        """
        Initialize simulation engine.
        
        Sets up:
        - Dependency injection container
        - Mock service factories
        - Synthetic data loader
        - Model loading infrastructure
        """
        if self._initialized:
            logger.warning("SimulationEngine already initialized")
            return

        logger.info("Initializing SimulationEngine...")

        # Register mock service factories
        # These will be implemented in Story AI17.2
        # For now, we just log that they need to be registered
        logger.debug("Mock service factories will be registered in Story AI17.2")

        # Create necessary directories
        self.config.results_directory.mkdir(parents=True, exist_ok=True)
        self.config.synthetic_data_directory.mkdir(parents=True, exist_ok=True)

        self._initialized = True
        logger.info("SimulationEngine initialized successfully")

    async def run_3am_simulation(
        self,
        home_ids: list[str] | None = None,
        max_parallel: int | None = None
    ) -> dict[str, Any]:
        """
        Run 3 AM workflow simulation.
        
        Args:
            home_ids: List of home IDs to simulate (None = use all available)
            max_parallel: Maximum parallel homes (None = use config default)
            
        Returns:
            Simulation results dictionary
        """
        if not self._initialized:
            await self.initialize()

        logger.info("Starting 3 AM workflow simulation...")
        logger.info(f"Mode: {self.config.mode}")
        logger.info(f"Model mode: {self.config.model_mode}")

        # This will be implemented in Story AI17.4
        # For now, return placeholder
        return {
            "status": "not_implemented",
            "message": "3 AM workflow simulation will be implemented in Story AI17.4",
            "home_ids": home_ids or [],
            "mode": self.config.mode
        }

    async def run_ask_ai_simulation(
        self,
        query_ids: list[str] | None = None,
        max_parallel: int | None = None
    ) -> dict[str, Any]:
        """
        Run Ask AI flow simulation.
        
        Args:
            query_ids: List of query IDs to simulate (None = use all available)
            max_parallel: Maximum parallel queries (None = use config default)
            
        Returns:
            Simulation results dictionary
        """
        if not self._initialized:
            await self.initialize()

        logger.info("Starting Ask AI flow simulation...")
        logger.info(f"Mode: {self.config.mode}")

        # This will be implemented in Story AI17.6
        # For now, return placeholder
        return {
            "status": "not_implemented",
            "message": "Ask AI flow simulation will be implemented in Story AI17.6",
            "query_ids": query_ids or [],
            "mode": self.config.mode
        }

    def get_workflow_simulator(self, workflow_type: str) -> Any:
        """
        Get workflow simulator.
        
        Args:
            workflow_type: "3am" or "ask_ai"
            
        Returns:
            Workflow simulator instance
        """
        if workflow_type == "3am":
            from ..workflows.daily_analysis_simulator import DailyAnalysisSimulator
            return DailyAnalysisSimulator(self.container)
        elif workflow_type == "ask_ai":
            from ..workflows.ask_ai_simulator import AskAISimulator
            return AskAISimulator(self.container)
        else:
            raise ValueError(f"Unknown workflow type: {workflow_type}")

    async def cleanup(self) -> None:
        """Cleanup resources."""
        logger.info("Cleaning up SimulationEngine...")
        self.container.clear()
        self._initialized = False
        logger.info("SimulationEngine cleaned up")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()

