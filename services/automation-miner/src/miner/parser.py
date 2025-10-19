"""
Automation Parser

Extracts structured metadata from Home Assistant automations with:
- YAML parsing
- Device/integration extraction
- Use case classification (ML-free, keyword-based)
- Complexity calculation
- Quality scoring
- PII removal
"""
import re
import yaml
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from .models import ParsedAutomation, AutomationMetadata

logger = logging.getLogger(__name__)


class AutomationParser:
    """Parse and normalize Home Assistant automations"""
    
    # Known device types in HA
    DEVICE_TYPES = {
        'light', 'switch', 'sensor', 'binary_sensor', 'motion_sensor',
        'door_sensor', 'window_sensor', 'temperature_sensor', 'humidity_sensor',
        'occupancy_sensor', 'lux_sensor', 'water_leak_sensor',
        'climate', 'thermostat', 'fan', 'cover', 'blind', 'shade',
        'lock', 'camera', 'alarm', 'media_player', 'tv',
        'vacuum', 'plug', 'outlet', 'socket'
    }
    
    # Known HA integrations
    INTEGRATIONS = {
        'mqtt', 'zigbee2mqtt', 'zha', 'zwave', 'hue', 'deconz',
        'esphome', 'tasmota', 'shelly', 'homekit', 'google_assistant',
        'alexa', 'weather', 'sun', 'person', 'zone', 'automation',
        'script', 'scene', 'input_boolean', 'input_select', 'timer'
    }
    
    # Use case keywords
    USE_CASE_KEYWORDS = {
        'energy': [
            'power', 'electricity', 'energy', 'watt', 'kwh', 'consumption',
            'solar', 'battery', 'charge', 'saving', 'efficient', 'cost'
        ],
        'comfort': [
            'temperature', 'climate', 'thermostat', 'heating', 'cooling',
            'light', 'lighting', 'brightness', 'ambiance', 'dim', 'scene',
            'comfort', 'cozy', 'warm', 'cool'
        ],
        'security': [
            'alarm', 'security', 'lock', 'door', 'window', 'motion',
            'camera', 'surveillance', 'armed', 'disarmed', 'alert',
            'notify', 'intrusion', 'smoke', 'fire', 'leak', 'safety'
        ],
        'convenience': [
            'automation', 'schedule', 'routine', 'presence', 'away',
            'home', 'vacation', 'sleep', 'wake', 'morning', 'evening',
            'night', 'reminder', 'notification'
        ]
    }
    
    def parse_yaml(self, yaml_str: str) -> Optional[Dict[str, Any]]:
        """
        Parse YAML automation structure
        
        Args:
            yaml_str: YAML string to parse
        
        Returns:
            Parsed automation dictionary or None if invalid
        """
        try:
            data = yaml.safe_load(yaml_str)
            
            # Handle blueprint format
            if isinstance(data, dict) and 'blueprint' in data:
                # Extract blueprint automation
                blueprint = data.get('blueprint', {})
                return blueprint
            
            return data
        
        except yaml.YAMLError as e:
            logger.warning(f"Failed to parse YAML: {e}")
            return None
    
    def extract_devices(self, automation: Dict[str, Any]) -> List[str]:
        """
        Extract device types from automation
        
        Looks for device types in entity IDs (e.g., light.bedroom -> light)
        """
        devices = set()
        
        def extract_from_entity(entity_id: str):
            """Extract device type from entity_id"""
            if not entity_id or not isinstance(entity_id, str):
                return
            
            # Entity format: domain.object_id
            parts = entity_id.split('.')
            if len(parts) >= 1:
                domain = parts[0]
                if domain in self.DEVICE_TYPES:
                    devices.add(domain)
        
        def recurse_dict(d):
            """Recursively search for entity IDs"""
            if isinstance(d, dict):
                for key, value in d.items():
                    if key in ['entity_id', 'entity']:
                        if isinstance(value, str):
                            extract_from_entity(value)
                        elif isinstance(value, list):
                            for entity in value:
                                extract_from_entity(entity)
                    else:
                        recurse_dict(value)
            elif isinstance(d, list):
                for item in d:
                    recurse_dict(item)
        
        recurse_dict(automation)
        
        return sorted(list(devices))
    
    def extract_integrations(self, automation: Dict[str, Any]) -> List[str]:
        """
        Extract HA integrations used in automation
        
        Looks for platform references and known integration names
        """
        integrations = set()
        
        def recurse_dict(d):
            """Recursively search for integration references"""
            if isinstance(d, dict):
                # Check for platform key
                if 'platform' in d:
                    platform = d['platform']
                    if platform in self.INTEGRATIONS:
                        integrations.add(platform)
                
                # Recurse
                for value in d.values():
                    recurse_dict(value)
            
            elif isinstance(d, list):
                for item in d:
                    recurse_dict(item)
        
        recurse_dict(automation)
        
        return sorted(list(integrations))
    
    def classify_use_case(
        self,
        automation: Dict[str, Any],
        title: str = "",
        description: str = ""
    ) -> str:
        """
        Classify automation use case using keyword matching
        
        ML-free approach: counts keyword matches for each category
        
        Returns:
            'energy', 'comfort', 'security', or 'convenience'
        """
        # Combine all text for analysis
        text = f"{title} {description} {str(automation)}".lower()
        
        # Count keyword matches for each category
        scores = {category: 0 for category in self.USE_CASE_KEYWORDS}
        
        for category, keywords in self.USE_CASE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    scores[category] += 1
        
        # Return category with highest score
        if max(scores.values()) == 0:
            # Default to convenience if no matches
            return 'convenience'
        
        return max(scores, key=scores.get)
    
    def calculate_complexity(self, automation: Dict[str, Any]) -> str:
        """
        Calculate automation complexity based on structure
        
        Args:
            automation: Parsed automation dictionary
        
        Returns:
            'low', 'medium', or 'high'
        """
        trigger_count = len(automation.get('trigger', []))
        condition_count = len(automation.get('condition', []))
        action_count = len(automation.get('action', []))
        
        total_elements = trigger_count + condition_count + action_count
        
        if total_elements <= 3:
            return 'low'
        elif total_elements <= 7:
            return 'medium'
        else:
            return 'high'
    
    def calculate_quality_score(
        self,
        votes: int,
        age_days: int,
        completeness: float
    ) -> float:
        """
        Calculate quality score (0.0-1.0)
        
        Formula: weighted average of vote score, recency, and completeness
        
        Args:
            votes: Number of community votes
            age_days: Age in days since creation
            completeness: Completeness score (0.0-1.0)
        
        Returns:
            Quality score between 0.0 and 1.0
        """
        # Vote score (logarithmic scale to prevent huge posts dominating)
        vote_score = min(1.0, (votes / 1000.0) ** 0.5)  # Cap at 1.0
        
        # Recency score (decay over 2 years)
        max_age = 730  # 2 years
        recency_score = max(0.0, 1.0 - (age_days / max_age))
        
        # Weighted average (votes: 50%, completeness: 30%, recency: 20%)
        quality = (
            0.5 * vote_score +
            0.3 * completeness +
            0.2 * recency_score
        )
        
        return round(quality, 3)
    
    def remove_pii(self, text: str) -> str:
        """
        Remove personally identifiable information from text
        
        Args:
            text: Input text
        
        Returns:
            Text with PII removed
        """
        # Remove entity IDs (e.g., light.bedroom_lamp -> light)
        text = re.sub(r'\b(light|switch|sensor|binary_sensor)\.[a-z0-9_]+', r'\1', text)
        
        # Remove IP addresses
        text = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP]', text)
        
        # Remove common personal names (basic pattern)
        # This is optional and may have false positives
        # text = re.sub(r'\b[A-Z][a-z]+\'s\b', '[NAME]\'s', text)
        
        return text
    
    def parse_automation(
        self,
        post_data: Dict[str, Any]
    ) -> Optional[ParsedAutomation]:
        """
        Parse automation from Discourse post data
        
        Args:
            post_data: Post data from DiscourseClient
        
        Returns:
            ParsedAutomation or None if parsing failed
        """
        yaml_blocks = post_data.get('yaml_blocks', [])
        title = post_data.get('title', '')
        description = post_data.get('description', '')
        
        # Try to parse YAML blocks
        parsed_yaml = None
        for yaml_block in yaml_blocks:
            parsed = self.parse_yaml(yaml_block)
            if parsed:
                parsed_yaml = parsed
                break  # Use first valid YAML
        
        if not parsed_yaml:
            # No valid YAML found, use description only
            logger.debug(f"No valid YAML for post {post_data.get('id')}, using description")
            parsed_yaml = {}
        
        # Extract components
        devices = self.extract_devices(parsed_yaml)
        integrations = self.extract_integrations(parsed_yaml)
        
        triggers = parsed_yaml.get('trigger', [])
        if not isinstance(triggers, list):
            triggers = [triggers] if triggers else []
        
        conditions = parsed_yaml.get('condition', [])
        if not isinstance(conditions, list):
            conditions = [conditions] if conditions else []
        
        actions = parsed_yaml.get('action', [])
        if not isinstance(actions, list):
            actions = [actions] if actions else []
        
        # Classify
        use_case = self.classify_use_case(parsed_yaml, title, description)
        complexity = self.calculate_complexity(parsed_yaml) if parsed_yaml else 'low'
        
        # Calculate completeness
        completeness = 0.0
        if yaml_blocks:
            completeness += 0.4
        if description:
            completeness += 0.3
        if devices:
            completeness += 0.2
        if triggers and actions:
            completeness += 0.1
        
        return ParsedAutomation(
            raw_yaml=yaml_blocks[0] if yaml_blocks else None,
            parsed_data=parsed_yaml,
            devices=devices,
            integrations=integrations,
            triggers=triggers,
            conditions=conditions,
            actions=actions,
            use_case=use_case,
            complexity=complexity,
            has_yaml=bool(yaml_blocks),
            has_description=bool(description),
            completeness_score=completeness
        )
    
    def create_metadata(
        self,
        post_data: Dict[str, Any],
        parsed: ParsedAutomation
    ) -> AutomationMetadata:
        """
        Create AutomationMetadata from parsed automation
        
        Args:
            post_data: Original post data
            parsed: Parsed automation
        
        Returns:
            Validated AutomationMetadata
        """
        title = post_data.get('title', 'Untitled Automation')
        description = post_data.get('description', '')
        
        # Remove PII
        title = self.remove_pii(title)
        description = self.remove_pii(description)
        
        # Calculate quality score
        votes = post_data.get('likes', 0)
        created_at = datetime.fromisoformat(
            post_data.get('created_at', datetime.utcnow().isoformat()).replace('Z', '+00:00')
        )
        age_days = (datetime.now(created_at.tzinfo) - created_at).days
        
        quality_score = self.calculate_quality_score(
            votes=votes,
            age_days=age_days,
            completeness=parsed.completeness_score
        )
        
        updated_at = datetime.fromisoformat(
            post_data.get('updated_at', created_at.isoformat()).replace('Z', '+00:00')
        )
        
        return AutomationMetadata(
            title=title,
            description=description[:2000],  # Limit length
            devices=parsed.devices,
            integrations=parsed.integrations,
            triggers=parsed.triggers,
            conditions=parsed.conditions,
            actions=parsed.actions,
            use_case=parsed.use_case or 'convenience',
            complexity=parsed.complexity or 'low',
            quality_score=quality_score,
            vote_count=votes,
            source='discourse',
            source_id=str(post_data.get('id', '')),
            created_at=created_at,
            updated_at=updated_at,
            metadata={
                'tags': post_data.get('tags', []),
                'views': post_data.get('views', 0),
                'author': post_data.get('author', ''),
                'has_yaml': parsed.has_yaml
            }
        )

