"""
Automation Generator Service

Converts synergies to Home Assistant automations using 2025 best practices.
Uses Home Assistant REST API for programmatic automation creation.

Based on PATTERNS_SYNERGIES_IMPROVEMENT_RECOMMENDATIONS.md

Phase 3 Enhancement: Blueprint-First Architecture
- Attempts to deploy via blueprint when a matching blueprint is found
- Falls back to YAML generation if no blueprint match
"""

import logging
import yaml
from typing import Any, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from shared.homeiq_automation.yaml_transformer import YAMLTransformer
from shared.homeiq_automation.blueprints import BlueprintPatternLibrary
from shared.homeiq_automation.schema import (
    HomeIQAutomation,
    HomeIQTrigger,
    HomeIQAction,
    HomeIQMetadata,
    DeviceContext,
    SafetyChecks
)
from .automation_pre_deployment_validator import AutomationPreDeploymentValidator

# Phase 3: Blueprint Deployment Integration
try:
    from ..blueprint_deployment import BlueprintDeployer, DeploymentRequest
    from ..blueprint_opportunity import BlueprintOpportunityEngine
    BLUEPRINT_DEPLOYMENT_AVAILABLE = True
except ImportError:
    BLUEPRINT_DEPLOYMENT_AVAILABLE = False

logger = logging.getLogger(__name__)


class AutomationGenerator:
    """
    Converts synergies to Home Assistant automations using 2025 best practices.
    
    Uses Home Assistant WebSocket/REST API for programmatic automation creation.
    References: /websites/developers_home-assistant_io (Context7)
    
    Phase 3 Enhancement: Blueprint-First Architecture
    - Prioritizes blueprint deployment over raw YAML generation
    - Falls back to YAML only when no suitable blueprint is found
    """
    
    def __init__(
        self,
        ha_url: str,
        ha_token: str,
        ha_version: str = "2025.1",
        blueprint_index_url: str | None = None,
        prefer_blueprints: bool = True,
    ):
        """
        Initialize automation generator.
        
        Args:
            ha_url: Home Assistant URL (e.g., "http://192.168.1.86:8123")
            ha_token: Home Assistant long-lived access token
            ha_version: Home Assistant version (default: 2025.1)
            blueprint_index_url: Optional Blueprint Index service URL (Phase 3)
            prefer_blueprints: If True, attempt blueprint deployment first (Phase 3)
        """
        self.ha_url = ha_url.rstrip('/')
        self.ha_token = ha_token
        self.ha_version = ha_version
        self.blueprint_index_url = blueprint_index_url
        self.prefer_blueprints = prefer_blueprints
        
        self.yaml_transformer = YAMLTransformer(ha_version=ha_version)
        self.blueprint_library = BlueprintPatternLibrary()
        self.validator = AutomationPreDeploymentValidator(ha_url=ha_url, ha_token=ha_token)
        
        # Phase 3: Initialize blueprint deployer if available
        self.blueprint_deployer: BlueprintDeployer | None = None
        self.blueprint_engine: BlueprintOpportunityEngine | None = None
        
        if BLUEPRINT_DEPLOYMENT_AVAILABLE and blueprint_index_url:
            self.blueprint_deployer = BlueprintDeployer(
                ha_url=ha_url,
                ha_token=ha_token,
                blueprint_index_url=blueprint_index_url,
            )
            self.blueprint_engine = BlueprintOpportunityEngine(
                blueprint_index_url=blueprint_index_url
            )
    
    async def generate_automation_from_synergy(
        self,
        synergy: dict[str, Any],
        ha_client: httpx.AsyncClient,
        db: Optional[AsyncSession] = None,
        device_inventory: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Generate and deploy Home Assistant automation from synergy.
        
        Phase 3: Blueprint-First Architecture
        - First attempts to find and deploy a matching blueprint
        - Falls back to YAML generation if no blueprint match
        
        Args:
            synergy: Synergy dictionary with devices, trigger_entity, action_entity, etc.
            ha_client: HTTP client for Home Assistant API calls
            db: Optional database session for pattern lookups
            device_inventory: Optional device inventory for blueprint auto-fill
        
        Returns:
            {
                'automation_id': str,
                'automation_yaml': str,
                'blueprint_id': str | None,
                'deployment_status': str,
                'estimated_impact': float,
                'deployment_method': str  # 'blueprint' or 'yaml'
            }
        """
        synergy_id = synergy.get('synergy_id', 'unknown')
        
        try:
            # Phase 3: Try blueprint deployment first
            if self.prefer_blueprints and self.blueprint_engine and self.blueprint_deployer:
                blueprint_result = await self._try_blueprint_deployment(
                    synergy=synergy,
                    device_inventory=device_inventory,
                    http_client=ha_client,
                )
                
                if blueprint_result:
                    logger.info(f"✅ Deployed synergy {synergy_id} via blueprint: {blueprint_result['blueprint_id']}")
                    return {
                        **blueprint_result,
                        'deployment_method': 'blueprint',
                        'estimated_impact': synergy.get('impact_score', 0.0),
                    }
                else:
                    logger.info(f"No matching blueprint for synergy {synergy_id}, falling back to YAML")
            
            # Fallback: YAML generation (original approach)
            return await self._generate_automation_via_yaml(
                synergy=synergy,
                ha_client=ha_client,
            )
            
        except Exception as e:
            logger.error(f"Failed to generate automation from synergy {synergy_id}: {e}", exc_info=True)
            raise
    
    async def _try_blueprint_deployment(
        self,
        synergy: dict[str, Any],
        device_inventory: list[dict[str, Any]] | None,
        http_client: httpx.AsyncClient,
    ) -> dict[str, Any] | None:
        """
        Attempt to deploy synergy via blueprint.
        
        Args:
            synergy: Synergy dictionary
            device_inventory: Device inventory for auto-fill
            http_client: HTTP client
            
        Returns:
            Deployment result dict or None if no blueprint match
        """
        if not self.blueprint_engine or not self.blueprint_deployer:
            return None
        
        try:
            # Find matching blueprints for this synergy
            matches = await self.blueprint_engine.find_blueprints_for_synergy(
                synergy=synergy,
                limit=1,  # Get best match only
            )
            
            if not matches:
                return None
            
            best_match = matches[0]
            
            # Only deploy if fit score is above threshold
            if best_match.fit_score < 0.6:
                logger.info(
                    f"Blueprint {best_match.blueprint_id} has low fit score "
                    f"({best_match.fit_score:.2f}), skipping"
                )
                return None
            
            # Prepare deployment request
            request = DeploymentRequest(
                blueprint_id=best_match.blueprint_id,
                automation_name=f"Synergy: {synergy.get('synergy_id', 'auto')}",
                description=f"Generated from synergy {synergy.get('synergy_id')} via blueprint",
                input_values={
                    k: v.suggested_entity
                    for k, v in best_match.auto_fill_suggestions.items()
                },
                use_auto_fill=True,
            )
            
            # Deploy
            result = await self.blueprint_deployer.deploy_blueprint(
                request=request,
                device_inventory=device_inventory,
                http_client=http_client,
            )
            
            if result.success:
                return {
                    'automation_id': result.automation_id,
                    'automation_yaml': result.automation_yaml,
                    'blueprint_id': best_match.blueprint_id,
                    'deployment_status': 'deployed',
                }
            else:
                logger.warning(f"Blueprint deployment failed: {result.error}")
                return None
                
        except Exception as e:
            logger.warning(f"Blueprint deployment attempt failed: {e}")
            return None
    
    async def _generate_automation_via_yaml(
        self,
        synergy: dict[str, Any],
        ha_client: httpx.AsyncClient,
    ) -> dict[str, Any]:
        """
        Generate automation via YAML transformation (fallback method).
        
        This is the original implementation, now used as a fallback when
        no suitable blueprint is found.
        """
        # 1. Convert synergy to HomeIQAutomation schema
        homeiq_automation = self._synergy_to_homeiq_automation(synergy)
        
        # 2. Transform to YAML using blueprint library or strict rules
        yaml_content = await self.yaml_transformer.transform_to_yaml(
            homeiq_automation,
            strategy="auto"  # Try blueprint first, then strict rules
        )
        
        # 2.5. Validate automation before deployment (Recommendation 4.2)
        validation_result = await self.validator.validate_automation(
            yaml_content,
            ha_client
        )
        
        if not validation_result['valid']:
            error_msg = f"Automation validation failed: {', '.join(validation_result['errors'])}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        if validation_result['warnings']:
            logger.warning(f"Automation validation warnings: {', '.join(validation_result['warnings'])}")
        
        # 3. Deploy via Home Assistant API (2025 best practice: use REST API)
        automation_id = await self._deploy_automation(
            ha_client,
            yaml_content,
            synergy.get('synergy_id')
        )
        
        # 4. Find matching blueprint (if used)
        blueprint_id = self.blueprint_library.find_matching_blueprint(homeiq_automation)
        
        return {
            'automation_id': automation_id,
            'automation_yaml': yaml_content,
            'blueprint_id': blueprint_id,
            'deployment_status': 'deployed',
            'deployment_method': 'yaml',
            'estimated_impact': synergy.get('impact_score', 0.0)
        }
    
    def _synergy_to_homeiq_automation(
        self,
        synergy: dict[str, Any]
    ) -> HomeIQAutomation:
        """
        Convert synergy dictionary to HomeIQAutomation schema.
        
        Args:
            synergy: Synergy dictionary with devices, trigger_entity, action_entity, etc.
        
        Returns:
            HomeIQAutomation object
        """
        # Extract device information
        devices = synergy.get('devices', [])
        if not devices and 'chain_devices' in synergy:
            devices = synergy['chain_devices']
        
        # Extract trigger and action entities
        trigger_entity = synergy.get('trigger_entity')
        action_entity = synergy.get('action_entity')
        
        # If no explicit trigger/action, use first two devices
        if not trigger_entity and len(devices) >= 1:
            trigger_entity = devices[0]
        if not action_entity and len(devices) >= 2:
            action_entity = devices[1]
        
        # Create trigger (state change on trigger entity)
        trigger = HomeIQTrigger(
            platform="state",
            entity_id=trigger_entity,
            to="on" if synergy.get('synergy_type') == 'device_pair' else None,
            device_id=trigger_entity,
            area_id=synergy.get('area')
        )
        
        # Create action (turn on/off action entity)
        action = HomeIQAction(
            service=f"{action_entity.split('.')[0]}.turn_on" if action_entity else "automation.turn_on",
            entity_id=action_entity,
            device_id=action_entity,
            area_id=synergy.get('area')
        )
        
        # Create device context
        device_context = DeviceContext(
            device_ids=devices,
            entity_ids=[e for e in [trigger_entity, action_entity] if e],
            device_types=[d.split('.')[0] for d in devices if '.' in d],
            area_ids=[synergy.get('area')] if synergy.get('area') else None
        )
        
        # Create metadata
        metadata = HomeIQMetadata(
            created_by="ai-pattern-service",
            pattern_id=None,  # Could link to pattern if available
            confidence_score=synergy.get('confidence', 0.0),
            use_case=self._infer_use_case(synergy),
            complexity=self._infer_complexity(synergy)
        )
        
        # Create safety checks
        safety_checks = SafetyChecks(
            requires_confirmation=False,  # Could be True for critical devices
            critical_devices=None,
            time_constraints=None
        )
        
        # Create base HomeIQAutomation
        automation = HomeIQAutomation(
            alias=f"Synergy: {synergy.get('synergy_id', 'auto')}",
            description=f"Generated from synergy {synergy.get('synergy_id')} - {synergy.get('rationale', '')}",
            triggers=[trigger],
            actions=[action],
            condition=None,  # Will be adjusted based on context_breakdown
            mode="single",  # Default mode
            homeiq_metadata=metadata,
            device_context=device_context,
            safety_checks=safety_checks
        )
        
        # Recommendation 4.1: Apply context-aware parameter adjustments
        automation = self._apply_context_aware_parameters(automation, synergy)
        
        return automation
    
    def _infer_use_case(
        self,
        synergy: dict[str, Any]
    ) -> str:
        """Infer use case from synergy data."""
        # Check context breakdown for hints
        context_breakdown = synergy.get('context_breakdown', {})
        if context_breakdown:
            if 'energy' in context_breakdown:
                return "energy"
            if 'security' in str(synergy.get('devices', [])).lower():
                return "security"
        
        # Check device types
        devices = synergy.get('devices', [])
        if any('climate' in d or 'thermostat' in d for d in devices):
            return "comfort"
        if any('light' in d for d in devices):
            return "convenience"
        
        return "convenience"  # Default
    
    def _infer_complexity(
        self,
        synergy: dict[str, Any]
    ) -> str:
        """Infer complexity from synergy data."""
        device_count = len(synergy.get('devices', []))
        if device_count <= 2:
            return "low"
        elif device_count <= 4:
            return "medium"
        else:
            return "high"
    
    def _apply_context_aware_parameters(
        self,
        automation: HomeIQAutomation,
        synergy: dict[str, Any]
    ) -> HomeIQAutomation:
        """
        Apply context-aware parameter adjustments to automation.
        
        Recommendation 4.1: Context-Aware Automation Parameters
        - Weather context → adjust climate automation thresholds
        - Energy context → optimize for energy savings
        - Time context → adjust delays based on time-of-day patterns
        
        Args:
            automation: HomeIQAutomation object to adjust
            synergy: Synergy dictionary with context_breakdown
            
        Returns:
            Adjusted HomeIQAutomation object
        """
        context_breakdown = synergy.get('context_breakdown', {})
        if not context_breakdown:
            return automation  # No context data, return as-is
        
        # Get action domain from first action
        action_domain = None
        if automation.actions and len(automation.actions) > 0:
            action_service = automation.actions[0].service
            if action_service and '.' in action_service:
                action_domain = action_service.split('.')[0]
        
        # Weather context → adjust climate automation parameters
        if 'weather' in context_breakdown or 'temperature' in context_breakdown:
            weather_data = context_breakdown.get('weather') or context_breakdown.get('temperature')
            if weather_data and action_domain == 'climate':
                # Adjust temperature based on weather
                adjusted_temp = self._adjust_temperature_for_weather(weather_data)
                if adjusted_temp and automation.actions:
                    # Update action parameters with adjusted temperature
                    # Note: This would require modifying the action's data field
                    logger.info(f"Applied weather-based temperature adjustment: {adjusted_temp}°F")
        
        # Energy context → optimize for energy savings
        if 'energy' in context_breakdown or 'energy_cost' in context_breakdown or 'peak_hours' in context_breakdown:
            energy_data = context_breakdown.get('energy') or context_breakdown.get('energy_cost') or context_breakdown.get('peak_hours')
            if energy_data:
                # Add condition to avoid peak hours if energy cost is high
                peak_hours = energy_data.get('peak_hours') if isinstance(energy_data, dict) else None
                if peak_hours:
                    # Add time condition to avoid peak hours
                    logger.info(f"Applied energy optimization: avoiding peak hours {peak_hours}")
        
        # Carbon context → optimize for low carbon intensity
        if 'carbon' in context_breakdown or 'carbon_intensity' in context_breakdown:
            carbon_data = context_breakdown.get('carbon') or context_breakdown.get('carbon_intensity')
            if carbon_data:
                carbon_intensity = carbon_data.get('intensity') if isinstance(carbon_data, dict) else carbon_data
                if isinstance(carbon_intensity, (int, float)) and carbon_intensity > 300:  # High carbon intensity
                    # Add delay or condition to wait for lower carbon intensity
                    logger.info(f"Applied carbon optimization: high intensity ({carbon_intensity}), may delay automation")
        
        # Time context → adjust delays based on time-of-day patterns
        if 'time' in context_breakdown or 'time_of_day' in context_breakdown:
            time_data = context_breakdown.get('time') or context_breakdown.get('time_of_day')
            if time_data:
                # Adjust delays based on time patterns
                delay = self._adjust_delay_for_time_context(time_data)
                if delay and automation.actions:
                    logger.info(f"Applied time-based delay adjustment: {delay}s")
        
        return automation
    
    def _adjust_temperature_for_weather(self, weather_data: dict[str, Any] | Any) -> float | None:
        """
        Adjust temperature based on weather context.
        
        Args:
            weather_data: Weather data from context_breakdown
            
        Returns:
            Adjusted temperature in Fahrenheit, or None if no adjustment
        """
        if not isinstance(weather_data, dict):
            return None
        
        current_temp = weather_data.get('temperature') or weather_data.get('temp')
        if not isinstance(current_temp, (int, float)):
            return None
        
        # Adjust target temperature based on current weather
        # If it's hot outside, set AC to lower temp
        # If it's cold outside, set heat to higher temp
        if current_temp > 80:  # Hot weather
            return 72.0  # Cooler target
        elif current_temp < 50:  # Cold weather
            return 68.0  # Warmer target
        else:
            return 70.0  # Moderate target
    
    def _adjust_delay_for_time_context(self, time_data: dict[str, Any] | Any) -> int | None:
        """
        Adjust automation delay based on time-of-day context.
        
        Args:
            time_data: Time context data from context_breakdown
            
        Returns:
            Delay in seconds, or None if no adjustment
        """
        if not isinstance(time_data, dict):
            return None
        
        hour = time_data.get('hour')
        if not isinstance(hour, int):
            return None
        
        # Adjust delays based on time of day
        # Morning (6-9 AM): shorter delays (people are active)
        # Night (10 PM - 6 AM): longer delays (people may be sleeping)
        if 6 <= hour < 9:
            return 2  # Short delay in morning
        elif 22 <= hour or hour < 6:
            return 10  # Longer delay at night
        else:
            return 5  # Default delay
    
    async def _deploy_automation(
        self,
        ha_client: httpx.AsyncClient,
        yaml_content: str,
        synergy_id: Optional[str] = None
    ) -> str:
        """
        Deploy automation to Home Assistant using REST API.
        
        Home Assistant 2025 API: POST /api/services/automation/create
        or use WebSocket: call_service domain="automation" service="create"
        
        Args:
            ha_client: HTTP client for Home Assistant API
            yaml_content: Automation YAML content
            synergy_id: Optional synergy ID for metadata
        
        Returns:
            Automation entity ID (e.g., "automation.synergy_abc123")
        """
        try:
            # Parse YAML to automation config dict
            automation_config = yaml.safe_load(yaml_content)
            
            # Ensure it's a list (Home Assistant expects list of automations)
            if not isinstance(automation_config, list):
                automation_config = [automation_config]
            
            # Add metadata to first automation
            if automation_config and isinstance(automation_config[0], dict):
                automation_config[0]['alias'] = automation_config[0].get(
                    'alias',
                    f"Synergy Automation: {synergy_id or 'auto'}"
                )
                automation_config[0]['description'] = automation_config[0].get(
                    'description',
                    f"Generated from synergy {synergy_id}"
                )
            
            # Deploy via REST API (2025 best practice)
            # Note: Home Assistant REST API expects automation config as dict, not list
            # We'll use the first automation in the list
            if automation_config:
                automation_dict = automation_config[0]
                
                response = await ha_client.post(
                    f"{self.ha_url}/api/services/automation/create",
                    headers={
                        "Authorization": f"Bearer {self.ha_token}",
                        "Content-Type": "application/json"
                    },
                    json=automation_dict
                )
                response.raise_for_status()
                
                # Return automation ID from response
                result = response.json()
                automation_id = result.get('entity_id') or result.get('id') or f"automation.synergy_{synergy_id or 'auto'}"
                logger.info(f"✅ Automation deployed: {automation_id}")
                return automation_id
            else:
                raise ValueError("No automation config to deploy")
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error deploying automation: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Failed to deploy automation: {e}", exc_info=True)
            raise
