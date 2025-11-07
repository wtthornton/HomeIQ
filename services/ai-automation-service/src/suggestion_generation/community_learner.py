"""
Community Pattern Learner

Learns from proven Home Assistant automations in the community:
- Popular blueprints
- Community forum examples
- GitHub automation repositories
- Validated patterns
"""

import logging
import json
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


# Community patterns database (can be loaded from external source)
COMMUNITY_PATTERNS = [
    {
        'pattern_id': 'motion_light',
        'name': 'Motion-Activated Lighting',
        'description': 'Turn on lights when motion detected',
        'trigger': 'binary_sensor.motion',
        'action': 'light.turn_on',
        'conditions': ['after_sunset', 'not_already_on'],
        'popularity': 1000,
        'category': 'convenience',
        'complexity': 'simple'
    },
    {
        'pattern_id': 'door_notification',
        'name': 'Door Open Notification',
        'description': 'Notify when door opens while away',
        'trigger': 'binary_sensor.door',
        'action': 'notify.mobile_app',
        'conditions': ['away_mode', 'door_state_changed'],
        'popularity': 800,
        'category': 'security',
        'complexity': 'simple'
    },
    {
        'pattern_id': 'presence_climate',
        'name': 'Presence-Based Climate Control',
        'description': 'Adjust climate when arriving/leaving',
        'trigger': 'person.arrives',
        'action': 'climate.set_temperature',
        'conditions': ['time_of_day', 'season'],
        'popularity': 600,
        'category': 'comfort',
        'complexity': 'medium'
    },
    {
        'pattern_id': 'sunset_lights',
        'name': 'Sunset Lighting',
        'description': 'Turn on lights at sunset',
        'trigger': 'sun.sunset',
        'action': 'light.turn_on',
        'conditions': ['presence_home'],
        'popularity': 900,
        'category': 'convenience',
        'complexity': 'simple'
    },
    {
        'pattern_id': 'temperature_fan',
        'name': 'Temperature-Based Fan Control',
        'description': 'Turn on fan when temperature exceeds threshold',
        'trigger': 'sensor.temperature',
        'action': 'fan.turn_on',
        'conditions': ['temperature_above_threshold', 'presence_home'],
        'popularity': 500,
        'category': 'comfort',
        'complexity': 'medium'
    },
    {
        'pattern_id': 'away_mode',
        'name': 'Away Mode Automation',
        'description': 'Activate away mode when everyone leaves',
        'trigger': 'all_persons_away',
        'action': 'scene.turn_on',
        'conditions': ['time_of_day'],
        'popularity': 700,
        'category': 'security',
        'complexity': 'medium'
    },
    {
        'pattern_id': 'morning_routine',
        'name': 'Morning Routine',
        'description': 'Turn on lights and adjust climate in morning',
        'trigger': 'time',
        'action': 'scene.turn_on',
        'conditions': ['weekday', 'presence_home'],
        'popularity': 750,
        'category': 'convenience',
        'complexity': 'medium'
    },
    {
        'pattern_id': 'night_mode',
        'name': 'Night Mode',
        'description': 'Dim lights and lock doors at night',
        'trigger': 'time',
        'action': 'scene.turn_on',
        'conditions': ['time_range', 'presence_home'],
        'popularity': 650,
        'category': 'security',
        'complexity': 'medium'
    }
]


class CommunityPatternLearner:
    """
    Learns from community Home Assistant automation patterns.
    
    Matches community-proven patterns to user's devices and context.
    """
    
    def __init__(self, patterns_db: Optional[List[Dict]] = None):
        """
        Initialize community pattern learner.
        
        Args:
            patterns_db: Optional list of community patterns (defaults to built-in)
        """
        self.patterns_db = patterns_db or COMMUNITY_PATTERNS
        logger.info(f"CommunityPatternLearner initialized with {len(self.patterns_db)} patterns")
    
    def match_patterns_to_user(
        self,
        user_devices: List[Dict],
        user_entities: List[Dict],
        user_context: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Match community patterns to user's devices.
        
        Args:
            user_devices: List of user's devices
            user_entities: List of user's entities
            user_context: Optional user context (areas, preferences, etc.)
            
        Returns:
            List of matched community patterns with user adaptations
        """
        matched = []
        
        # Create lookup dictionaries
        entity_domains = {e.get('entity_id', ''): e.get('domain', '') 
                         for e in user_entities if e.get('entity_id')}
        
        for pattern in self.patterns_db:
            # Check if user has required devices
            if self._can_apply_pattern(pattern, entity_domains, user_entities):
                adapted = self._adapt_pattern(pattern, user_entities, user_context)
                if adapted:
                    matched.append(adapted)
        
        # Sort by popularity and relevance
        matched.sort(key=lambda x: (
            x.get('popularity', 0),
            x.get('relevance_score', 0)
        ), reverse=True)
        
        logger.info(f"Matched {len(matched)} community patterns to user devices")
        return matched
    
    def _can_apply_pattern(
        self,
        pattern: Dict,
        entity_domains: Dict[str, str],
        user_entities: List[Dict]
    ) -> bool:
        """Check if pattern can be applied to user's devices."""
        trigger = pattern.get('trigger', '')
        action = pattern.get('action', '')
        
        # Extract domains
        trigger_domain = trigger.split('.')[0] if '.' in trigger else ''
        action_domain = action.split('.')[0] if '.' in action else ''
        
        # Check if user has devices in these domains
        has_trigger = any(
            e.get('domain') == trigger_domain or 
            trigger_domain in str(e.get('entity_id', ''))
            for e in user_entities
        )
        
        has_action = any(
            e.get('domain') == action_domain or
            action_domain in str(e.get('entity_id', ''))
            for e in user_entities
        )
        
        return has_trigger and has_action
    
    def _adapt_pattern(
        self,
        pattern: Dict,
        user_entities: List[Dict],
        user_context: Optional[Dict]
    ) -> Optional[Dict]:
        """Adapt community pattern to user's specific devices."""
        # Find matching entities
        trigger = pattern.get('trigger', '')
        action = pattern.get('action', '')
        
        trigger_domain = trigger.split('.')[0] if '.' in trigger else ''
        action_domain = action.split('.')[0] if '.' in action else ''
        
        # Find user entities in these domains
        trigger_entities = [
            e for e in user_entities
            if e.get('domain') == trigger_domain or trigger_domain in str(e.get('entity_id', ''))
        ]
        action_entities = [
            e for e in user_entities
            if e.get('domain') == action_domain or action_domain in str(e.get('entity_id', ''))
        ]
        
        if not trigger_entities or not action_entities:
            return None
        
        # Use first matching entities (can be enhanced to select best match)
        trigger_entity = trigger_entities[0].get('entity_id', '')
        action_entity = action_entities[0].get('entity_id', '')
        
        adapted = {
            'pattern_id': pattern['pattern_id'],
            'name': pattern['name'],
            'description': pattern['description'],
            'trigger_entity': trigger_entity,
            'action_entity': action_entity,
            'conditions': pattern.get('conditions', []),
            'popularity': pattern.get('popularity', 0),
            'category': pattern.get('category', 'convenience'),
            'complexity': pattern.get('complexity', 'simple'),
            'relevance_score': 0.8,  # Can be calculated based on device match quality
            'metadata': {
                'source': 'community',
                'original_pattern': pattern,
                'adaptation': 'auto'
            }
        }
        
        return adapted
    
    def get_pattern_by_id(self, pattern_id: str) -> Optional[Dict]:
        """Get community pattern by ID."""
        for pattern in self.patterns_db:
            if pattern.get('pattern_id') == pattern_id:
                return pattern
        return None
    
    def get_patterns_by_category(self, category: str) -> List[Dict]:
        """Get community patterns by category."""
        return [p for p in self.patterns_db if p.get('category') == category]
    
    def get_top_patterns(self, limit: int = 10) -> List[Dict]:
        """Get top N most popular patterns."""
        sorted_patterns = sorted(
            self.patterns_db,
            key=lambda x: x.get('popularity', 0),
            reverse=True
        )
        return sorted_patterns[:limit]





