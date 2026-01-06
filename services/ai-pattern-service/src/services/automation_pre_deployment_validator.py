"""
Automation Pre-Deployment Validator

Validates automations before deployment using Home Assistant 2025 API.
Prevents invalid automations from being deployed.

Based on PATTERNS_SYNERGIES_IMPROVEMENT_RECOMMENDATIONS.md - Recommendation 4.2
"""

import logging
import yaml
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class AutomationPreDeploymentValidator:
    """
    Validate automations before deployment using Home Assistant 2025 API.
    
    Uses Home Assistant REST API to validate:
    - Entity IDs exist: GET /api/states/{entity_id}
    - Services are available: GET /api/services
    - Automation config structure is valid
    """
    
    def __init__(self, ha_url: str, ha_token: str):
        """
        Initialize validator.
        
        Args:
            ha_url: Home Assistant URL
            ha_token: Home Assistant long-lived access token
        """
        self.ha_url = ha_url.rstrip('/')
        self.ha_token = ha_token
    
    async def validate_automation(
        self,
        automation_yaml: str,
        ha_client: httpx.AsyncClient
    ) -> dict[str, Any]:
        """
        Validate automation before deployment using Home Assistant API.
        
        Args:
            automation_yaml: Automation YAML content
            ha_client: HTTP client for Home Assistant API calls
        
        Returns:
            {
                'valid': bool,
                'errors': list[str],
                'warnings': list[str],
                'suggestions': list[str],
                'entity_validation': dict[str, bool],
                'service_validation': dict[str, bool]
            }
        """
        errors = []
        warnings = []
        suggestions = []
        entity_validation = {}
        service_validation = {}
        
        # Parse YAML
        try:
            automation_config = yaml.safe_load(automation_yaml)
        except yaml.YAMLError as e:
            return {
                'valid': False,
                'errors': [f"YAML parsing error: {e}"],
                'warnings': [],
                'suggestions': [],
                'entity_validation': {},
                'service_validation': {}
            }
        
        # Handle list of automations (Home Assistant format)
        if isinstance(automation_config, list):
            if not automation_config:
                return {
                    'valid': False,
                    'errors': ["Empty automation list"],
                    'warnings': [],
                    'suggestions': [],
                    'entity_validation': {},
                    'service_validation': {}
                }
            automation_config = automation_config[0]  # Validate first automation
        
        if not isinstance(automation_config, dict):
            return {
                'valid': False,
                'errors': ["Invalid automation config format"],
                'warnings': [],
                'suggestions': [],
                'entity_validation': {},
                'service_validation': {}
            }
        
        # 1. Validate automation config structure
        required_fields = ['trigger', 'action']
        for field in required_fields:
            if field not in automation_config:
                errors.append(f"Missing required field: {field}")
        
        # 2. Validate entities exist (2025 API: GET /api/states/{entity_id})
        entities_to_check = self._extract_entity_ids(automation_config)
        for entity_id in entities_to_check:
            try:
                response = await ha_client.get(
                    f"{self.ha_url}/api/states/{entity_id}",
                    headers={"Authorization": f"Bearer {self.ha_token}"},
                    timeout=5.0
                )
                entity_validation[entity_id] = response.status_code == 200
                if response.status_code != 200:
                    errors.append(f"Entity {entity_id} does not exist or is not accessible")
                else:
                    # Check if entity is unavailable
                    state_data = response.json()
                    if state_data.get('state') == 'unavailable':
                        warnings.append(f"Entity {entity_id} is currently unavailable")
            except httpx.TimeoutException:
                entity_validation[entity_id] = False
                warnings.append(f"Timeout checking entity {entity_id} - may be slow to respond")
            except Exception as e:
                entity_validation[entity_id] = False
                errors.append(f"Error checking entity {entity_id}: {e}")
        
        # 3. Validate services are available (2025 API: GET /api/services)
        services_to_check = self._extract_services(automation_config)
        try:
            response = await ha_client.get(
                f"{self.ha_url}/api/services",
                headers={"Authorization": f"Bearer {self.ha_token}"},
                timeout=5.0
            )
            available_services = response.json() if response.status_code == 200 else {}
            
            for service in services_to_check:
                domain, service_name = service.split('.', 1) if '.' in service else (service, '')
                service_validation[service] = (
                    domain in available_services and
                    service_name in available_services.get(domain, {})
                )
                if not service_validation[service]:
                    errors.append(f"Service {service} is not available")
        except httpx.TimeoutException:
            warnings.append("Timeout checking services - service validation skipped")
        except Exception as e:
            warnings.append(f"Could not validate services: {e}")
        
        # 4. Check for common issues
        if 'condition' in automation_config:
            if isinstance(automation_config['condition'], list) and not automation_config['condition']:
                warnings.append("Empty condition list - automation may always trigger")
        
        # 5. Check trigger validity
        triggers = automation_config.get('trigger', [])
        if not triggers:
            errors.append("No triggers defined - automation will never run")
        elif isinstance(triggers, list):
            for i, trigger in enumerate(triggers):
                if not isinstance(trigger, dict):
                    errors.append(f"Trigger {i} is not a valid dictionary")
                elif 'platform' not in trigger:
                    errors.append(f"Trigger {i} missing required 'platform' field")
        
        # 6. Check action validity
        actions = automation_config.get('action', [])
        if not actions:
            errors.append("No actions defined - automation will do nothing")
        elif isinstance(actions, list):
            for i, action in enumerate(actions):
                if not isinstance(action, dict):
                    errors.append(f"Action {i} is not a valid dictionary")
                elif 'service' not in action and 'scene' not in action:
                    errors.append(f"Action {i} missing required 'service' or 'scene' field")
        
        # 7. Suggestions for improvement
        if 'alias' not in automation_config:
            suggestions.append("Add an 'alias' field for better automation identification")
        
        if 'description' not in automation_config:
            suggestions.append("Add a 'description' field to document automation purpose")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'suggestions': suggestions,
            'entity_validation': entity_validation,
            'service_validation': service_validation
        }
    
    def _extract_entity_ids(self, config: dict[str, Any]) -> list[str]:
        """
        Extract all entity IDs from automation config.
        
        Recursively finds entity_id fields in triggers, conditions, and actions.
        """
        entities = set()
        self._traverse_and_extract_entities(config, entities)
        return list(entities)
    
    def _traverse_and_extract_entities(self, data: Any, entities: set[str]) -> None:
        """
        Recursively traverse automation structure and extract entity IDs.
        
        Args:
            data: Data structure to traverse (dict, list, or value)
            entities: Set to add entity IDs to
        """
        if isinstance(data, dict):
            for key, value in data.items():
                if key == 'entity_id':
                    if isinstance(value, str):
                        entities.add(value)
                    elif isinstance(value, list):
                        entities.update(value)
                elif key == 'target' and isinstance(value, dict) and 'entity_id' in value:
                    target_entity_id = value['entity_id']
                    if isinstance(target_entity_id, str):
                        entities.add(target_entity_id)
                    elif isinstance(target_entity_id, list):
                        entities.update(target_entity_id)
                else:
                    self._traverse_and_extract_entities(value, entities)
        elif isinstance(data, list):
            for item in data:
                self._traverse_and_extract_entities(item, entities)
    
    def _extract_services(self, config: dict[str, Any]) -> list[str]:
        """
        Extract all service calls from automation config.
        
        Finds service calls in actions.
        """
        services = set()
        self._traverse_and_extract_services(config, services)
        return list(services)
    
    def _traverse_and_extract_services(self, data: Any, services: set[str]) -> None:
        """
        Recursively traverse automation structure and extract service calls.
        
        Args:
            data: Data structure to traverse (dict, list, or value)
            services: Set to add service names to
        """
        if isinstance(data, dict):
            if 'service' in data:
                service_name = data['service']
                if isinstance(service_name, str):
                    services.add(service_name)
            elif 'scene' in data:
                # Scene is also a service call
                scene_name = data.get('scene')
                if scene_name:
                    services.add(f"scene.turn_on")
            
            for value in data.values():
                self._traverse_and_extract_services(value, services)
        elif isinstance(data, list):
            for item in data:
                self._traverse_and_extract_services(item, services)
