"""
Enhanced Synthetic Home Generator

Integrates all Epic AI-11 enhancements into a unified pipeline:
- HA 2024 naming conventions (Story AI11.1)
- Areas/Floors/Labels hierarchy (Story AI11.2)
- Expanded failure scenarios (Story AI11.4)
- Event type diversification (Story AI11.5)
- Blueprint automation templates (Story AI11.6)
- Context-aware event generation (Story AI11.7)
- Multi-device synergies (Story AI11.8)
- Ground truth validation (Story AI11.3)

Epic AI-11: End-to-End Pipeline Integration
"""

import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Any

from .synthetic_area_generator import SyntheticAreaGenerator
from .synthetic_device_generator import SyntheticDeviceGenerator
from .synthetic_event_generator import SyntheticEventGenerator
try:
    from .synthetic_automation_generator import SyntheticAutomationGenerator
except ImportError:
    # Fallback if automation generator not available
    SyntheticAutomationGenerator = None
from .context_correlator import ContextCorrelator
from .synergy_patterns import SynergyPatternGenerator
from .validation.ground_truth_generator import GroundTruthGenerator

logger = logging.getLogger(__name__)


class EnhancedSyntheticHomeGenerator:
    """
    Enhanced synthetic home generator with all Epic AI-11 enhancements.
    
    Pipeline:
    1. Generate home data
    2. Generate areas (with floors/labels)
    3. Generate devices (with HA 2024 naming)
    4. Assign failure scenarios
    5. Generate automations (blueprint templates)
    6. Generate events (diversified types)
    7. Apply context-aware patterns
    8. Generate synergy events
    9. Generate ground truth
    """
    
    def __init__(self):
        """Initialize enhanced synthetic home generator."""
        self.area_generator = SyntheticAreaGenerator()
        self.device_generator = SyntheticDeviceGenerator()
        self.event_generator = SyntheticEventGenerator()
        self.automation_generator = SyntheticAutomationGenerator() if SyntheticAutomationGenerator else None
        self.context_correlator = ContextCorrelator()
        self.synergy_generator = SynergyPatternGenerator()
        self.ground_truth_generator = GroundTruthGenerator()
        
        logger.info("EnhancedSyntheticHomeGenerator initialized with all Epic AI-11 enhancements")
    
    async def generate_complete_home(
        self,
        home_data: dict[str, Any],
        days: int = 7,
        enable_context: bool = True,
        enable_synergies: bool = True,
        enable_ground_truth: bool = True,
        weather_data: list[dict[str, Any]] | None = None,
        carbon_data: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        """
        Generate a complete synthetic home with all enhancements.
        
        Args:
            home_data: Home configuration data
            days: Number of days of events to generate
            enable_context: Enable context-aware patterns
            enable_synergies: Enable synergy patterns
            enable_ground_truth: Generate ground truth annotations
            weather_data: Optional weather data for context correlation
            carbon_data: Optional carbon intensity data for context correlation
        
        Returns:
            Complete synthetic home dictionary
        """
        start_time = time.time()
        logger.info(f"Generating complete home: {home_data.get('home_type', 'unknown')}")
        
        # Step 1: Generate areas (with floors/labels) - Story AI11.2
        logger.debug("Step 1: Generating areas...")
        areas = self.area_generator.generate_areas(home_data)
        logger.debug(f"Generated {len(areas)} areas")
        
        # Step 2: Generate devices (with HA 2024 naming) - Story AI11.1
        logger.debug("Step 2: Generating devices...")
        devices = self.device_generator.generate_devices(home_data, areas)
        logger.debug(f"Generated {len(devices)} devices")
        
        # Step 3: Failure scenarios already assigned in device generation - Story AI11.4
        
        # Step 4: Generate automations (blueprint templates) - Story AI11.6
        automations = []
        if self.automation_generator:
            logger.debug("Step 4: Generating automations...")
            automations = self.automation_generator.generate_automations(devices, areas)
            logger.debug(f"Generated {len(automations)} automations")
        else:
            logger.debug("Step 4: Automation generator not available, skipping")
        
        # Step 5: Generate events (diversified types) - Story AI11.5
        logger.debug("Step 5: Generating events...")
        events = await self.event_generator.generate_events(devices, days=days)
        logger.debug(f"Generated {len(events)} events")
        
        # Step 6: Apply context-aware patterns - Story AI11.7
        if enable_context:
            logger.debug("Step 6: Applying context-aware patterns...")
            start_date = datetime.now(timezone.utc) - timedelta(days=days)
            events = self.context_correlator.apply_context_patterns(
                events=events,
                devices=devices,
                weather_data=weather_data,
                carbon_data=carbon_data,
                start_date=start_date
            )
            logger.debug(f"Applied context patterns to {len(events)} events")
        
        # Step 7: Generate synergy events - Story AI11.8
        if enable_synergies:
            logger.debug("Step 7: Generating synergy events...")
            start_date = datetime.now(timezone.utc) - timedelta(days=days)
            synergy_events = self.synergy_generator.generate_synergy_events(
                devices=devices,
                automations=automations,
                start_date=start_date,
                days=days
            )
            # Merge synergy events with regular events
            events.extend(synergy_events)
            logger.debug(f"Generated {len(synergy_events)} synergy events")
        
        # Step 8: Generate ground truth - Story AI11.3
        ground_truth = None
        if enable_ground_truth:
            logger.debug("Step 8: Generating ground truth...")
            ground_truth = self.ground_truth_generator.generate_ground_truth(
                home_data=home_data,
                devices=devices,
                areas=areas
            )
            logger.debug(f"Generated ground truth with {len(ground_truth.expected_patterns)} patterns")
        
        # Assemble complete home
        complete_home = {
            **home_data,
            'areas': areas,
            'devices': devices,
            'automations': automations,
            'events': events,
            'ground_truth': ground_truth.model_dump() if ground_truth else None,
            'generation_metadata': {
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'days': days,
                'enhancements': {
                    'ha_2024_naming': True,
                    'areas_floors_labels': True,
                    'failure_scenarios': True,
                    'event_diversification': True,
                    'blueprint_automations': True,
                    'context_aware': enable_context,
                    'synergies': enable_synergies,
                    'ground_truth': enable_ground_truth
                },
                'generation_time_ms': int((time.time() - start_time) * 1000)
            }
        }
        
        logger.info(f"✅ Generated complete home in {complete_home['generation_metadata']['generation_time_ms']}ms")
        return complete_home
    
    async def generate_batch(
        self,
        home_data_list: list[dict[str, Any]],
        days: int = 7,
        enable_context: bool = True,
        enable_synergies: bool = True,
        enable_ground_truth: bool = True,
        progress_callback=None
    ) -> list[dict[str, Any]]:
        """
        Generate a batch of complete synthetic homes.
        
        Args:
            home_data_list: List of home configuration data
            days: Number of days of events to generate per home
            enable_context: Enable context-aware patterns
            enable_synergies: Enable synergy patterns
            enable_ground_truth: Generate ground truth annotations
            progress_callback: Optional callback(home_num, total_homes, home)
        
        Returns:
            List of complete synthetic home dictionaries
        """
        total_homes = len(home_data_list)
        logger.info(f"Generating batch of {total_homes} homes...")
        
        complete_homes = []
        for i, home_data in enumerate(home_data_list):
            home_num = i + 1
            try:
                complete_home = await self.generate_complete_home(
                    home_data=home_data,
                    days=days,
                    enable_context=enable_context,
                    enable_synergies=enable_synergies,
                    enable_ground_truth=enable_ground_truth
                )
                complete_homes.append(complete_home)
                
                if progress_callback:
                    progress_callback(home_num, total_homes, complete_home)
                
                logger.info(f"✅ [{home_num}/{total_homes}] Generated home: {home_data.get('home_type', 'unknown')}")
            except Exception as e:
                logger.error(f"❌ [{home_num}/{total_homes}] Failed to generate home: {e}")
                continue
        
        logger.info(f"✅ Generated {len(complete_homes)}/{total_homes} homes")
        return complete_homes

