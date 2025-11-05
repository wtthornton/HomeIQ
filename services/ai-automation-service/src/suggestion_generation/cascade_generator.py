"""
Cascade Automation Suggestion Generator

Generates progressive automation suggestions that build on each other:
- Level 1: Basic automation
- Level 2: Add conditions
- Level 3: Add enhancements
- Level 4: Add intelligence
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class CascadeSuggestionGenerator:
    """
    Generates cascade (progressive) automation suggestions.
    
    Creates multiple suggestions from simple to complex, allowing
    users to gradually enhance their automations.
    """
    
    def __init__(self, llm_client=None):
        """
        Initialize cascade suggestion generator.
        
        Args:
            llm_client: Optional LLM client for generating enhanced suggestions
        """
        self.llm_client = llm_client
        logger.info("CascadeSuggestionGenerator initialized")
    
    def generate_cascade(
        self,
        base_pattern: Dict,
        device_context: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Generate cascade of automation suggestions from simple to complex.
        
        Args:
            base_pattern: Base pattern dictionary
            device_context: Optional device context with capabilities
            
        Returns:
            List of suggestion dictionaries, ordered from simple to complex
        """
        suggestions = []
        
        # Level 1: Basic automation
        level1 = self._generate_level1(base_pattern, device_context)
        if level1:
            suggestions.append(level1)
        
        # Level 2: Add conditions
        level2 = self._generate_level2(base_pattern, device_context, level1)
        if level2:
            suggestions.append(level2)
        
        # Level 3: Add enhancements
        level3 = self._generate_level3(base_pattern, device_context, level2 or level1)
        if level3:
            suggestions.append(level3)
        
        # Level 4: Add intelligence
        level4 = self._generate_level4(base_pattern, device_context, level3 or level2 or level1)
        if level4:
            suggestions.append(level4)
        
        logger.info(f"Generated {len(suggestions)} cascade suggestions for pattern {base_pattern.get('device_id')}")
        return suggestions
    
    def _generate_level1(self, pattern: Dict, device_context: Optional[Dict]) -> Optional[Dict]:
        """Generate Level 1: Basic automation (simple, direct)."""
        pattern_type = pattern.get('pattern_type', 'unknown')
        device_id = pattern.get('device_id', '')
        
        if pattern_type == 'time_of_day':
            hour = pattern.get('hour', 0)
            minute = pattern.get('minute', 0)
            return {
                'level': 1,
                'title': f"Turn on {device_id} at {hour:02d}:{minute:02d}",
                'description': f"Simple time-based automation: Turn on {device_id} at {hour:02d}:{minute:02d} every day.",
                'confidence': 0.95,
                'complexity': 'simple',
                'enhancement_type': 'basic'
            }
        elif pattern_type == 'co_occurrence':
            device1 = pattern.get('device1', '')
            device2 = pattern.get('device2', '')
            return {
                'level': 1,
                'title': f"When {device1} activates, turn on {device2}",
                'description': f"Basic co-occurrence: When {device1} turns on, automatically turn on {device2}.",
                'confidence': 0.90,
                'complexity': 'simple',
                'enhancement_type': 'basic'
            }
        
        return None
    
    def _generate_level2(
        self,
        pattern: Dict,
        device_context: Optional[Dict],
        previous: Optional[Dict]
    ) -> Optional[Dict]:
        """Generate Level 2: Add conditions (time, presence, etc.)."""
        if not previous:
            return None
        
        pattern_type = pattern.get('pattern_type', 'unknown')
        
        enhancements = []
        
        if pattern_type == 'time_of_day':
            enhancements.append("Only when someone is home")
            enhancements.append("Only during weekdays")
            enhancements.append("Skip if already on")
        
        elif pattern_type == 'co_occurrence':
            enhancements.append("Only during specific hours")
            enhancements.append("Only when home")
            enhancements.append("Add delay before activating")
        
        if enhancements:
            return {
                'level': 2,
                'title': f"{previous.get('title', '')} (with conditions)",
                'description': f"Enhanced version: {previous.get('description', '')} {', '.join(enhancements[:2])}.",
                'confidence': 0.85,
                'complexity': 'medium',
                'enhancement_type': 'conditions',
                'previous_level': 1
            }
        
        return None
    
    def _generate_level3(
        self,
        pattern: Dict,
        device_context: Optional[Dict],
        previous: Optional[Dict]
    ) -> Optional[Dict]:
        """Generate Level 3: Add enhancements (dimming, delays, etc.)."""
        if not previous:
            return None
        
        enhancements = []
        
        # Check device capabilities from context
        if device_context:
            capabilities = device_context.get('capabilities', [])
            if 'brightness' in str(capabilities).lower():
                enhancements.append("with brightness control")
            if 'color' in str(capabilities).lower():
                enhancements.append("with color transitions")
            if 'timer' in str(capabilities).lower():
                enhancements.append("with auto-off timer")
        
        if not enhancements:
            enhancements.append("with auto-off after inactivity")
            enhancements.append("with smooth transitions")
        
        return {
            'level': 3,
            'title': f"{previous.get('title', '')} (enhanced)",
            'description': f"Advanced version: {previous.get('description', '')} {', '.join(enhancements[:2])}.",
            'confidence': 0.80,
            'complexity': 'advanced',
            'enhancement_type': 'enhancements',
            'previous_level': previous.get('level', 2)
        }
    
    def _generate_level4(
        self,
        pattern: Dict,
        device_context: Optional[Dict],
        previous: Optional[Dict]
    ) -> Optional[Dict]:
        """Generate Level 4: Add intelligence (context-aware, adaptive)."""
        if not previous:
            return None
        
        intelligence_features = []
        
        # Check for multi-factor patterns
        if pattern.get('pattern_type') == 'multi_factor':
            factors = pattern.get('metadata', {}).get('factors', [])
            intelligence_features.append(f"context-aware ({', '.join(factors[:2])})")
        
        intelligence_features.extend([
            "weather-responsive",
            "adaptive timing based on usage",
            "learns from user adjustments"
        ])
        
        return {
            'level': 4,
            'title': f"{previous.get('title', '')} (intelligent)",
            'description': f"Intelligent version: {previous.get('description', '')} {', '.join(intelligence_features[:2])}.",
            'confidence': 0.75,
            'complexity': 'expert',
            'enhancement_type': 'intelligence',
            'previous_level': previous.get('level', 3)
        }

