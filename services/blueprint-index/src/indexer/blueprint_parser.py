"""Blueprint YAML parser for extracting metadata."""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional
import uuid

import yaml

from ..models import IndexedBlueprint, BlueprintInput

logger = logging.getLogger(__name__)


# Custom YAML constructor for !input tags
def _input_constructor(loader, node):
    """Handle !input tags in blueprint YAML."""
    return f"!input {loader.construct_scalar(node)}"


# Register the constructor
yaml.add_constructor('!input', _input_constructor, Loader=yaml.SafeLoader)


class BlueprintParser:
    """
    Parser for Home Assistant blueprint YAML files.
    
    Extracts:
    - Blueprint metadata (name, description, domain)
    - Input definitions with domain/device_class requirements
    - Trigger and action information
    - Use case classification
    - Complexity estimation
    """
    
    # Known device domains
    DEVICE_DOMAINS = {
        'light', 'switch', 'sensor', 'binary_sensor', 'climate', 'cover',
        'fan', 'lock', 'media_player', 'vacuum', 'camera', 'alarm_control_panel',
        'water_heater', 'humidifier', 'scene', 'script', 'automation',
        'input_boolean', 'input_number', 'input_select', 'input_text',
        'device_tracker', 'person', 'zone', 'sun', 'weather', 'notify',
    }
    
    # Use case classification keywords
    USE_CASE_KEYWORDS = {
        'energy': ['power', 'electricity', 'energy', 'watt', 'kwh', 'solar', 'battery', 'consumption', 'saving'],
        'comfort': ['temperature', 'climate', 'thermostat', 'heating', 'cooling', 'light', 'brightness', 'comfort', 'warm', 'cool'],
        'security': ['alarm', 'security', 'lock', 'door', 'window', 'motion', 'camera', 'surveillance', 'alert', 'intrusion'],
        'convenience': ['automation', 'schedule', 'routine', 'presence', 'away', 'home', 'wake', 'sleep', 'reminder'],
    }
    
    def parse_yaml(self, yaml_content: str) -> Optional[dict[str, Any]]:
        """
        Parse YAML content and return parsed data.
        
        Args:
            yaml_content: Raw YAML string
            
        Returns:
            Parsed YAML dictionary or None if invalid
        """
        try:
            return yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            logger.warning(f"Failed to parse YAML: {e}")
            return None
    
    def is_blueprint(self, yaml_data: dict[str, Any]) -> bool:
        """Check if parsed YAML is a blueprint."""
        return isinstance(yaml_data, dict) and 'blueprint' in yaml_data
    
    def parse_blueprint(
        self,
        yaml_content: str,
        source_url: str,
        source_type: str = "github",
        source_id: Optional[str] = None,
        stars: int = 0,
        author: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> Optional[IndexedBlueprint]:
        """
        Parse a blueprint YAML and extract all metadata.
        
        Args:
            yaml_content: Raw YAML content
            source_url: URL where the blueprint was found
            source_type: Source type ('github', 'discourse', 'manual')
            source_id: External ID from source
            stars: Community stars/likes
            author: Blueprint author
            created_at: Creation timestamp
            updated_at: Last update timestamp
            
        Returns:
            IndexedBlueprint model or None if parsing fails
        """
        try:
            yaml_data = self.parse_yaml(yaml_content)
            if not yaml_data or not self.is_blueprint(yaml_data):
                return None
            
            blueprint_meta = yaml_data.get('blueprint', {})
            
            # Extract basic metadata
            name = blueprint_meta.get('name', 'Unnamed Blueprint')
            description = blueprint_meta.get('description', '')
            domain = blueprint_meta.get('domain', 'automation')
            
            # Extract input definitions
            inputs_raw = blueprint_meta.get('input', {})
            inputs, required_domains, required_device_classes = self._extract_inputs(inputs_raw)
            
            # Extract trigger information
            triggers = yaml_data.get('trigger', yaml_data.get('triggers', []))
            if not isinstance(triggers, list):
                triggers = [triggers] if triggers else []
            trigger_platforms = self._extract_trigger_platforms(triggers)
            
            # Extract action information
            actions = yaml_data.get('action', yaml_data.get('actions', []))
            if not isinstance(actions, list):
                actions = [actions] if actions else []
            action_services = self._extract_action_services(actions)
            
            # Additional domains from triggers/actions
            trigger_domains = self._extract_domains_from_structure(triggers)
            action_domains = self._extract_domains_from_structure(actions)
            
            # Combine all required domains
            all_domains = list(set(required_domains) | trigger_domains | action_domains)
            
            # Classify use case
            use_case = self._classify_use_case(name, description, yaml_data)
            
            # Calculate complexity
            complexity = self._calculate_complexity(triggers, actions, yaml_data.get('condition', []))
            
            # Calculate quality score
            quality_score = self._calculate_quality_score(
                has_description=bool(description),
                has_inputs=bool(inputs),
                complexity=complexity,
                stars=stars,
            )
            
            # Extract HA version requirements
            ha_min_version = blueprint_meta.get('min_version') or blueprint_meta.get('homeassistant', {}).get('min_version')
            
            # Create indexed blueprint
            blueprint = IndexedBlueprint(
                id=str(uuid.uuid4()),
                source_url=source_url,
                source_type=source_type,
                source_id=source_id,
                name=name,
                description=description[:2000] if description else None,
                domain=domain,
                required_domains=all_domains,
                required_device_classes=list(required_device_classes),
                inputs=inputs,
                trigger_platforms=trigger_platforms,
                action_services=action_services,
                use_case=use_case,
                tags=blueprint_meta.get('tags', []),
                stars=stars,
                community_rating=min(1.0, stars / 100) if stars else 0.0,  # Normalize stars
                quality_score=quality_score,
                complexity=complexity,
                has_description=bool(description),
                has_inputs=bool(inputs),
                author=author,
                ha_min_version=ha_min_version,
                created_at=created_at or datetime.now(timezone.utc),
                updated_at=updated_at or datetime.now(timezone.utc),
                indexed_at=datetime.now(timezone.utc),
                yaml_content=yaml_content,
            )
            
            return blueprint
            
        except Exception as e:
            logger.error(f"Failed to parse blueprint from {source_url}: {e}", exc_info=True)
            return None
    
    def _extract_inputs(
        self, 
        inputs_raw: dict[str, Any]
    ) -> tuple[dict[str, Any], list[str], set[str]]:
        """
        Extract input definitions and requirements.
        
        Returns:
            Tuple of (inputs dict, required_domains list, required_device_classes set)
        """
        inputs = {}
        required_domains = []
        required_device_classes = set()
        
        for input_name, input_def in inputs_raw.items():
            if not isinstance(input_def, dict):
                continue
            
            input_info = {
                'name': input_def.get('name', input_name),
                'description': input_def.get('description'),
                'default': input_def.get('default'),
            }
            
            selector = input_def.get('selector', {})
            
            # Entity selector
            if 'entity' in selector:
                entity_sel = selector['entity']
                domain = entity_sel.get('domain')
                device_class = entity_sel.get('device_class')
                
                input_info['selector_type'] = 'entity'
                input_info['domain'] = domain
                input_info['device_class'] = device_class
                
                if domain:
                    if isinstance(domain, list):
                        required_domains.extend(domain)
                    else:
                        required_domains.append(domain)
                
                if device_class:
                    if isinstance(device_class, list):
                        required_device_classes.update(device_class)
                    else:
                        required_device_classes.add(device_class)
            
            # Device selector
            elif 'device' in selector:
                device_sel = selector['device']
                input_info['selector_type'] = 'device'
                input_info['integration'] = device_sel.get('integration')
            
            # Target selector
            elif 'target' in selector:
                target_sel = selector['target']
                input_info['selector_type'] = 'target'
                
                if 'entity' in target_sel:
                    domain = target_sel['entity'].get('domain')
                    if domain:
                        if isinstance(domain, list):
                            required_domains.extend(domain)
                        else:
                            required_domains.append(domain)
            
            # Other selectors
            elif 'number' in selector:
                input_info['selector_type'] = 'number'
            elif 'text' in selector:
                input_info['selector_type'] = 'text'
            elif 'boolean' in selector:
                input_info['selector_type'] = 'boolean'
            elif 'time' in selector:
                input_info['selector_type'] = 'time'
            elif 'select' in selector:
                input_info['selector_type'] = 'select'
                input_info['options'] = selector['select'].get('options', [])
            
            inputs[input_name] = input_info
        
        return inputs, list(set(required_domains)), required_device_classes
    
    def _extract_trigger_platforms(self, triggers: list[Any]) -> list[str]:
        """Extract trigger platforms from trigger list."""
        platforms = set()
        
        for trigger in triggers:
            if isinstance(trigger, dict):
                platform = trigger.get('platform') or trigger.get('trigger')
                if platform:
                    platforms.add(str(platform))
        
        return list(platforms)
    
    def _extract_action_services(self, actions: list[Any]) -> list[str]:
        """Extract service calls from action list."""
        services = set()
        
        def recurse(obj):
            if isinstance(obj, dict):
                service = obj.get('service') or obj.get('action')
                if service and isinstance(service, str):
                    services.add(service)
                for value in obj.values():
                    recurse(value)
            elif isinstance(obj, list):
                for item in obj:
                    recurse(item)
        
        recurse(actions)
        return list(services)
    
    def _extract_domains_from_structure(self, structure: Any) -> set[str]:
        """Extract device domains from automation structure."""
        domains = set()
        
        def recurse(obj):
            if isinstance(obj, dict):
                # Check service calls
                service = obj.get('service') or obj.get('action')
                if service and isinstance(service, str) and '.' in service:
                    domain = service.split('.')[0]
                    if domain in self.DEVICE_DOMAINS:
                        domains.add(domain)
                
                # Check entity_id references
                entity_id = obj.get('entity_id')
                if entity_id and isinstance(entity_id, str) and '.' in entity_id:
                    if not entity_id.startswith('!input'):
                        domain = entity_id.split('.')[0]
                        if domain in self.DEVICE_DOMAINS:
                            domains.add(domain)
                
                for value in obj.values():
                    recurse(value)
            elif isinstance(obj, list):
                for item in obj:
                    recurse(item)
        
        recurse(structure)
        return domains
    
    def _classify_use_case(
        self, 
        name: str, 
        description: str, 
        yaml_data: dict[str, Any]
    ) -> str:
        """Classify blueprint use case based on keywords."""
        text = f"{name} {description} {str(yaml_data)}".lower()
        
        scores = {category: 0 for category in self.USE_CASE_KEYWORDS}
        
        for category, keywords in self.USE_CASE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    scores[category] += 1
        
        if max(scores.values()) == 0:
            return 'convenience'  # Default
        
        return max(scores, key=scores.get)
    
    def _calculate_complexity(
        self, 
        triggers: list[Any], 
        actions: list[Any], 
        conditions: Any
    ) -> str:
        """Calculate blueprint complexity."""
        trigger_count = len(triggers)
        action_count = len(actions) if isinstance(actions, list) else 1
        condition_count = len(conditions) if isinstance(conditions, list) else (1 if conditions else 0)
        
        total = trigger_count + action_count + condition_count
        
        if total <= 3:
            return 'low'
        elif total <= 7:
            return 'medium'
        else:
            return 'high'
    
    def _calculate_quality_score(
        self,
        has_description: bool,
        has_inputs: bool,
        complexity: str,
        stars: int,
    ) -> float:
        """
        Calculate quality score (0.0 - 1.0).
        
        Components:
        - Has description: 0.2
        - Has inputs: 0.2
        - Complexity appropriate: 0.2
        - Community stars: 0.4 (normalized)
        """
        score = 0.0
        
        if has_description:
            score += 0.2
        
        if has_inputs:
            score += 0.2
        
        # Complexity bonus (medium is optimal)
        if complexity == 'medium':
            score += 0.2
        elif complexity == 'low':
            score += 0.15
        else:
            score += 0.1
        
        # Stars contribution (logarithmic scale)
        if stars > 0:
            import math
            star_score = min(0.4, (math.log10(stars + 1) / 3) * 0.4)
            score += star_score
        
        return min(1.0, score)
