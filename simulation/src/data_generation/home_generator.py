"""
Enhanced Home Generator Wrapper

Wrapper around production SyntheticHomeGenerator for simulation use.
Provides on-demand generation with varied parameters.
"""

import logging
import sys
from pathlib import Path
from typing import Any

# Add production service to path for imports
PRODUCTION_SERVICE_PATH = Path(__file__).parent.parent.parent.parent / "services" / "ai-automation-service"
sys.path.insert(0, str(PRODUCTION_SERVICE_PATH))

try:
    from src.training.enhanced_synthetic_home_generator import EnhancedSyntheticHomeGenerator
    from src.training.synthetic_home_generator import SyntheticHomeGenerator
except ImportError:
    # Fallback if enhanced version not available
    try:
        from src.training.synthetic_home_generator import SyntheticHomeGenerator
        EnhancedSyntheticHomeGenerator = None
    except ImportError as e:
        raise ImportError(
            f"Failed to import SyntheticHomeGenerator from production service: {e}. "
            "Ensure the production service is available."
        )

logger = logging.getLogger(__name__)


class HomeGenerator:
    """
    Wrapper around production SyntheticHomeGenerator for simulation use.
    
    Provides:
    - On-demand generation for simulation runs
    - Varied parameters (home types, sizes, event days)
    - Ground truth annotation support
    - Error handling and validation
    """

    def __init__(self):
        """Initialize home generator wrapper."""
        # Use enhanced generator if available, otherwise fallback to basic
        if EnhancedSyntheticHomeGenerator:
            self.generator = EnhancedSyntheticHomeGenerator()
            logger.info("Using EnhancedSyntheticHomeGenerator")
        else:
            self.generator = SyntheticHomeGenerator()
            logger.info("Using SyntheticHomeGenerator (basic)")
        
        logger.info("HomeGenerator wrapper initialized")

    async def generate_home(
        self,
        home_type: str,
        event_days: int = 90,
        home_index: int = 0,
        enable_ground_truth: bool = True
    ) -> dict[str, Any]:
        """
        Generate a single synthetic home.
        
        Args:
            home_type: Home type (e.g., "single_family_house", "apartment")
            event_days: Number of days of events to generate
            home_index: Home index for uniqueness
            enable_ground_truth: Enable ground truth annotations
            
        Returns:
            Complete synthetic home dictionary
        """
        logger.debug(f"Generating home: type={home_type}, days={event_days}, index={home_index}")
        
        # Create home data template
        home_data = {
            "home_type": home_type,
            "home_id": f"sim_home_{home_index}_{home_type}",
            "home_name": f"Simulation Home {home_index}",
        }
        
        try:
            # Use enhanced generator if available
            if isinstance(self.generator, EnhancedSyntheticHomeGenerator):
                home = await self.generator.generate_complete_home(
                    home_data=home_data,
                    days=event_days,
                    enable_context=True,
                    enable_synergies=True,
                    enable_ground_truth=enable_ground_truth
                )
            else:
                # Fallback to basic generator
                homes = self.generator.generate_homes(
                    target_count=1,
                    home_types=[home_type]
                )
                if not homes:
                    raise ValueError(f"Failed to generate home of type {home_type}")
                home = homes[0]
                # Add home_id if missing
                if "home_id" not in home:
                    home["home_id"] = home_data["home_id"]
            
            # Ensure required fields
            if "home_id" not in home:
                home["home_id"] = home_data["home_id"]
            if "home_type" not in home:
                home["home_type"] = home_type
            
            logger.info(f"Generated home: {home['home_id']} ({len(home.get('devices', []))} devices, {len(home.get('events', []))} events)")
            return home
            
        except Exception as e:
            logger.error(f"Failed to generate home {home_type} #{home_index}: {e}")
            raise

    async def generate_homes(
        self,
        home_count: int,
        home_types: list[str] | None = None,
        event_days: int = 90,
        enable_ground_truth: bool = True
    ) -> list[dict[str, Any]]:
        """
        Generate multiple synthetic homes.
        
        Args:
            home_count: Number of homes to generate
            home_types: Home types to generate (default: all types)
            event_days: Number of days of events per home
            enable_ground_truth: Enable ground truth annotations
            
        Returns:
            List of synthetic home dictionaries
        """
        logger.info(f"Generating {home_count} homes (types: {home_types}, days: {event_days})")
        
        if home_types is None:
            home_types = list(SyntheticHomeGenerator.HOME_TYPE_DISTRIBUTION.keys())
        
        # Distribute homes across types
        homes_per_type = home_count // len(home_types)
        remainder = home_count % len(home_types)
        
        homes = []
        home_index = 0
        
        for home_type in home_types:
            count = homes_per_type + (1 if remainder > 0 else 0)
            remainder -= 1
            
            for i in range(count):
                try:
                    home = await self.generate_home(
                        home_type=home_type,
                        event_days=event_days,
                        home_index=home_index,
                        enable_ground_truth=enable_ground_truth
                    )
                    homes.append(home)
                    home_index += 1
                except Exception as e:
                    logger.error(f"Failed to generate home {home_index}: {e}")
                    continue
        
        logger.info(f"Generated {len(homes)}/{home_count} homes")
        return homes

