"""
Ground Truth Generator

Generate ground truth annotations for synthetic homes.
Extracts patterns, synergies, and validation baselines from generated events.
"""

import logging
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)


class GroundTruthGenerator:
    """
    Ground truth generator for synthetic homes.
    
    Extracts:
    - Ground truth patterns from generated events
    - Expected synergies from device relationships
    - Validation baselines
    - Pattern metadata (confidence, occurrences)
    """

    def __init__(self):
        """Initialize ground truth generator."""
        logger.info("GroundTruthGenerator initialized")

    def extract_patterns(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Extract patterns from events.
        
        Args:
            events: List of event dictionaries
            
        Returns:
            List of extracted patterns with metadata
        """
        patterns = []
        
        # Group events by entity_id
        entity_events = defaultdict(list)
        for event in events:
            entity_id = event.get("entity_id")
            if entity_id:
                entity_events[entity_id].append(event)
        
        # Extract patterns (state transitions, time-based patterns)
        for entity_id, entity_event_list in entity_events.items():
            if len(entity_event_list) < 2:
                continue
            
            # Find state transitions
            state_transitions = []
            for i in range(len(entity_event_list) - 1):
                prev_state = entity_event_list[i].get("state")
                next_state = entity_event_list[i + 1].get("state")
                
                if prev_state != next_state:
                    state_transitions.append({
                        "from_state": prev_state,
                        "to_state": next_state,
                        "timestamp": entity_event_list[i + 1].get("timestamp")
                    })
            
            if state_transitions:
                pattern = {
                    "entity_id": entity_id,
                    "pattern_type": "state_transition",
                    "transitions": state_transitions,
                    "occurrences": len(state_transitions),
                    "confidence": min(1.0, len(state_transitions) / 10.0)  # Higher confidence with more occurrences
                }
                patterns.append(pattern)
        
        logger.debug(f"Extracted {len(patterns)} patterns from {len(events)} events")
        return patterns

    def extract_synergies(
        self,
        devices: list[dict[str, Any]],
        events: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Extract expected synergies from device relationships.
        
        Args:
            devices: List of device dictionaries
            events: List of event dictionaries
            
        Returns:
            List of expected synergies
        """
        synergies = []
        
        # Group events by device/entity
        device_events = defaultdict(list)
        for event in events:
            entity_id = event.get("entity_id")
            device_id = event.get("device_id")
            if entity_id:
                device_events[entity_id].append(event)
        
        # Find co-occurring device activations
        device_states = {}
        for entity_id, entity_event_list in device_events.items():
            # Get most recent state
            if entity_event_list:
                device_states[entity_id] = entity_event_list[-1].get("state")
        
        # Find potential synergies (devices that activate together)
        entity_pairs = []
        for i, (entity1, state1) in enumerate(device_states.items()):
            for entity2, state2 in list(device_states.items())[i + 1:]:
                # Check if both are "on" or active
                if (state1 in ["on", "active", "open"] and 
                    state2 in ["on", "active", "open"]):
                    entity_pairs.append((entity1, entity2))
        
        # Create synergy entries
        for entity1, entity2 in entity_pairs:
            synergy = {
                "entity_1": entity1,
                "entity_2": entity2,
                "synergy_type": "co_activation",
                "confidence": 0.7,  # Default confidence for co-occurrence
                "occurrences": 1
            }
            synergies.append(synergy)
        
        logger.debug(f"Extracted {len(synergies)} synergies from {len(devices)} devices")
        return synergies

    def generate_ground_truth(
        self,
        home_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Generate complete ground truth for a synthetic home.
        
        Args:
            home_data: Synthetic home data dictionary
            
        Returns:
            Ground truth dictionary with patterns, synergies, and baselines
        """
        logger.debug(f"Generating ground truth for home: {home_data.get('home_id')}")
        
        devices = home_data.get("devices", [])
        events = home_data.get("events", [])
        
        # Extract patterns
        patterns = self.extract_patterns(events)
        
        # Extract synergies
        synergies = self.extract_synergies(devices, events)
        
        # Create ground truth structure
        ground_truth = {
            "home_id": home_data.get("home_id"),
            "home_type": home_data.get("home_type"),
            "patterns": patterns,
            "synergies": synergies,
            "metadata": {
                "total_devices": len(devices),
                "total_events": len(events),
                "pattern_count": len(patterns),
                "synergy_count": len(synergies)
            }
        }
        
        logger.info(
            f"Generated ground truth: {len(patterns)} patterns, {len(synergies)} synergies"
        )
        
        return ground_truth

    def export_ground_truth(
        self,
        ground_truth: dict[str, Any],
        format: str = "dict"
    ) -> dict[str, Any] | str:
        """
        Export ground truth in standardized format.
        
        Args:
            ground_truth: Ground truth dictionary
            format: Export format ("dict" or "json")
            
        Returns:
            Exported ground truth (dict or JSON string)
        """
        if format == "json":
            import json
            return json.dumps(ground_truth, indent=2)
        else:
            return ground_truth

