"""
Blueprint-Dataset Correlation Service

Correlates home-assistant-datasets automation tasks with blueprints
from the automation-miner to enhance pattern detection, synergy detection,
and YAML generation.

Phase 1: Blueprint-Dataset Correlation Service
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class BlueprintDatasetCorrelator:
    """
    Correlate blueprints with dataset automations.
    
    Matches dataset automation tasks to blueprints based on:
    - Device types (60% weight)
    - Use case alignment (30% weight)
    - Integration compatibility (10% weight)
    """
    
    def __init__(self, miner=None):
        """
        Initialize blueprint-dataset correlator.
        
        Args:
            miner: MinerIntegration instance for fetching blueprints
                  (optional, can be set later)
        """
        self.miner = miner
        logger.info("BlueprintDatasetCorrelator initialized")
    
    def set_miner(self, miner):
        """Set the miner integration instance"""
        self.miner = miner
    
    async def find_blueprint_for_dataset_task(
        self,
        dataset_task: dict[str, Any],
        miner=None
    ) -> dict[str, Any] | None:
        """
        Find matching blueprint for dataset automation task.
        
        Args:
            dataset_task: Dataset automation task with:
                - description: Task description
                - devices: List of device types/entities
                - expected_automation: Expected automation structure
            miner: MinerIntegration instance (optional, uses self.miner if not provided)
        
        Returns:
            Dictionary with blueprint match and correlation score, or None if no match:
            {
                'blueprint': {...},
                'fit_score': 0.0-1.0,
                'correlation_score': 0.0-1.0,
                'device_match': True/False,
                'use_case_match': True/False
            }
        """
        if not miner:
            miner = self.miner
        
        if not miner:
            logger.warning("No miner integration available, cannot find blueprints")
            return None
        
        # Extract device types from dataset task
        devices = self._extract_devices_from_task(dataset_task)
        
        if not devices:
            logger.debug("No devices found in dataset task")
            return None
        
        # Extract use case from description
        use_case = self._extract_use_case(dataset_task.get('description', ''))
        
        # Search blueprints
        try:
            blueprints = await self._search_blueprints(
                devices=devices,
                use_case=use_case,
                miner=miner
            )
        except Exception as e:
            logger.error(f"Error searching blueprints: {e}")
            return None
        
        if not blueprints:
            logger.debug(f"No blueprints found for devices: {devices}, use_case: {use_case}")
            return None
        
        # Find best match
        best_match = None
        best_score = 0.0
        
        for blueprint in blueprints:
            correlation_score = self._calculate_correlation_score(
                blueprint=blueprint,
                dataset_task=dataset_task,
                devices=devices,
                use_case=use_case
            )
            
            if correlation_score > best_score:
                best_score = correlation_score
                best_match = {
                    'blueprint': blueprint,
                    'fit_score': correlation_score,
                    'correlation_score': correlation_score,
                    'device_match': self._check_device_match(blueprint, devices),
                    'use_case_match': self._check_use_case_match(blueprint, use_case),
                    'devices': devices,
                    'use_case': use_case
                }
        
        if best_match and best_score > 0.5:  # Minimum threshold
            logger.info(
                f"Found blueprint match: {best_match['blueprint'].get('title', 'Unknown')} "
                f"(score: {best_score:.3f})"
            )
            return best_match
        
        return None
    
    async def find_blueprint_for_pattern(
        self,
        pattern: dict[str, Any],
        miner=None
    ) -> dict[str, Any] | None:
        """
        Find matching blueprint for detected pattern.
        
        Args:
            pattern: Detected pattern dictionary with device1, device2, etc.
            miner: MinerIntegration instance (optional)
        
        Returns:
            Blueprint match dictionary or None
        """
        # Convert pattern to dataset task format
        device1 = pattern.get('device1', '')
        device2 = pattern.get('device2', '')
        
        if not device1 or not device2:
            return None
        
        # Extract device types
        devices = []
        for device in [device1, device2]:
            if '.' in device:
                domain = device.split('.')[0]
                devices.append(domain)
            else:
                devices.append(device)
        
        # Create pseudo dataset task
        dataset_task = {
            'description': f"Pattern: {device1} → {device2}",
            'devices': devices,
            'pattern_type': pattern.get('pattern_type', 'co_occurrence')
        }
        
        return await self.find_blueprint_for_dataset_task(dataset_task, miner)
    
    def _extract_devices_from_task(self, task: dict[str, Any]) -> list[str]:
        """
        Extract device types from dataset task.
        
        Args:
            task: Dataset task dictionary
        
        Returns:
            List of device types (e.g., ['light', 'binary_sensor'])
        """
        devices = []
        
        # Try explicit devices list
        if 'devices' in task:
            for device in task['devices']:
                if isinstance(device, str):
                    # Extract domain from entity_id (e.g., 'light.kitchen' → 'light')
                    if '.' in device:
                        domain = device.split('.')[0]
                        if domain not in devices:
                            devices.append(domain)
                    else:
                        if device not in devices:
                            devices.append(device)
        
        # Try extracting from description
        if not devices:
            description = task.get('description', '')
            # Common device patterns
            device_patterns = {
                'light': r'\b(light|lights|lighting)\b',
                'motion': r'\b(motion|motion sensor)\b',
                'door': r'\b(door|door sensor)\b',
                'lock': r'\b(lock|locks)\b',
                'climate': r'\b(climate|thermostat|hvac)\b',
                'switch': r'\b(switch|switches)\b',
                'sensor': r'\b(sensor|sensors)\b'
            }
            
            for device_type, pattern in device_patterns.items():
                if re.search(pattern, description, re.IGNORECASE):
                    if device_type not in devices:
                        devices.append(device_type)
        
        # Try extracting from expected_automation
        if not devices and 'expected_automation' in task:
            expected = task['expected_automation']
            if isinstance(expected, dict):
                # Look for entity_id patterns
                entity_ids = self._extract_entity_ids_from_dict(expected)
                for entity_id in entity_ids:
                    if '.' in entity_id:
                        domain = entity_id.split('.')[0]
                        if domain not in devices:
                            devices.append(domain)
        
        return devices
    
    def _extract_entity_ids_from_dict(self, data: dict, entity_ids: list[str] = None) -> list[str]:
        """Recursively extract entity IDs from dictionary"""
        if entity_ids is None:
            entity_ids = []
        
        for key, value in data.items():
            if key == 'entity_id' and isinstance(value, str):
                if value not in entity_ids:
                    entity_ids.append(value)
            elif isinstance(value, dict):
                self._extract_entity_ids_from_dict(value, entity_ids)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        self._extract_entity_ids_from_dict(item, entity_ids)
                    elif isinstance(item, str) and '.' in item and key == 'entity_id':
                        if item not in entity_ids:
                            entity_ids.append(item)
        
        return entity_ids
    
    def _extract_use_case(self, description: str) -> str:
        """
        Extract use case from description.
        
        Args:
            description: Task description
        
        Returns:
            Use case string: 'comfort', 'security', 'energy', 'convenience', or 'unknown'
        """
        description_lower = description.lower()
        
        # Security keywords
        security_keywords = ['security', 'lock', 'door', 'alert', 'notification', 'alarm', 'intrusion']
        if any(keyword in description_lower for keyword in security_keywords):
            return 'security'
        
        # Energy keywords
        energy_keywords = ['energy', 'power', 'save', 'efficient', 'consumption', 'watt']
        if any(keyword in description_lower for keyword in energy_keywords):
            return 'energy'
        
        # Comfort keywords
        comfort_keywords = ['comfort', 'temperature', 'climate', 'hvac', 'thermostat', 'light', 'brightness']
        if any(keyword in description_lower for keyword in comfort_keywords):
            return 'comfort'
        
        # Convenience keywords
        convenience_keywords = ['convenience', 'automate', 'routine', 'schedule', 'time']
        if any(keyword in description_lower for keyword in convenience_keywords):
            return 'convenience'
        
        return 'unknown'
    
    async def _search_blueprints(
        self,
        devices: list[str],
        use_case: str,
        miner
    ) -> list[dict[str, Any]]:
        """
        Search for blueprints matching devices and use case.
        
        Args:
            devices: List of device types
            use_case: Use case string
            miner: MinerIntegration instance
        
        Returns:
            List of blueprint dictionaries
        """
        try:
            # Search by primary device type
            primary_device = devices[0] if devices else None
            
            # Map device types to blueprint search terms
            device_mapping = {
                'binary_sensor': 'motion_sensor',  # Common blueprint variable name
                'sensor': 'sensor',
                'light': 'light',
                'lock': 'lock',
                'climate': 'climate',
                'switch': 'switch'
            }
            
            search_device = device_mapping.get(primary_device, primary_device)
            
            # Search blueprints
            if use_case != 'unknown':
                blueprints = await miner.search_blueprints(
                    device=search_device,
                    use_case=use_case,
                    min_quality=0.7,
                    limit=20
                )
            else:
                blueprints = await miner.search_blueprints(
                    device=search_device,
                    min_quality=0.7,
                    limit=20
                )
            
            # search_blueprints returns a list directly
            return blueprints if isinstance(blueprints, list) else []
            
        except Exception as e:
            logger.error(f"Error searching blueprints: {e}")
            return []
    
    def _calculate_correlation_score(
        self,
        blueprint: dict[str, Any],
        dataset_task: dict[str, Any],
        devices: list[str],
        use_case: str
    ) -> float:
        """
        Calculate correlation score between blueprint and dataset task.
        
        Args:
            blueprint: Blueprint dictionary
            dataset_task: Dataset task dictionary
            devices: List of device types
            use_case: Use case string
        
        Returns:
            Correlation score (0.0-1.0)
        """
        score = 0.0
        
        # Device type match (60% weight)
        blueprint_devices = self._extract_blueprint_devices(blueprint)
        device_match = self._check_device_match(blueprint, devices)
        
        if device_match:
            # Calculate device overlap
            overlap = len(set(blueprint_devices) & set(devices))
            total = len(set(blueprint_devices) | set(devices))
            device_score = (overlap / total) if total > 0 else 0.0
            score += device_score * 0.6
        
        # Use case match (30% weight)
        use_case_match = self._check_use_case_match(blueprint, use_case)
        if use_case_match:
            score += 0.3
        
        # Integration compatibility (10% weight)
        # For now, assume compatible if devices match
        if device_match:
            score += 0.1
        
        return min(1.0, score)
    
    def _extract_blueprint_devices(self, blueprint: dict[str, Any]) -> list[str]:
        """Extract device types from blueprint"""
        devices = []
        
        # Try metadata
        metadata = blueprint.get('metadata', {})
        blueprint_devices = metadata.get('_blueprint_devices', [])
        if blueprint_devices:
            devices.extend(blueprint_devices)
        
        # Try blueprint variables
        blueprint_vars = metadata.get('_blueprint_variables', {})
        for var_name, var_def in blueprint_vars.items():
            if isinstance(var_def, dict):
                domain = var_def.get('domain')
                if domain and domain not in devices:
                    devices.append(domain)
        
        # Try devices field
        blueprint_devices_field = blueprint.get('devices', [])
        if blueprint_devices_field:
            devices.extend(blueprint_devices_field)
        
        return list(set(devices))  # Remove duplicates
    
    def _check_device_match(
        self,
        blueprint: dict[str, Any],
        devices: list[str]
    ) -> bool:
        """Check if blueprint devices match dataset devices"""
        blueprint_devices = self._extract_blueprint_devices(blueprint)
        
        if not blueprint_devices or not devices:
            return False
        
        # Check for overlap
        overlap = set(blueprint_devices) & set(devices)
        return len(overlap) > 0
    
    def _check_use_case_match(
        self,
        blueprint: dict[str, Any],
        use_case: str
    ) -> bool:
        """Check if blueprint use case matches dataset use case"""
        if use_case == 'unknown':
            return True  # Don't penalize if use case unknown
        
        blueprint_use_case = blueprint.get('use_case', '')
        
        if not blueprint_use_case:
            return True  # Don't penalize if blueprint has no use case
        
        return blueprint_use_case.lower() == use_case.lower()

