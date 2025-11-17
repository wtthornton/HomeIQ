"""
Service Validator

Validates service calls against entity capabilities and available services.
Epic 2025: Ensure only valid service calls are used in YAML generation.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger(__name__)


class ServiceValidator:
    """Validate service calls against entity capabilities"""
    
    def __init__(self, db_session: Optional[AsyncSession] = None):
        """
        Initialize the service validator.
        
        Args:
            db_session: Optional database session for entity lookups
        """
        self.db_session = db_session
    
    async def validate_service_call(
        self,
        entity_id: str,
        service: str,
        db_session: Optional[AsyncSession] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate that a service call is available for an entity.
        
        Args:
            entity_id: Entity ID to validate
            service: Service call (e.g., "light.turn_on")
            db_session: Optional database session (uses self.db_session if not provided)
        
        Returns:
            (is_valid, error_message)
        """
        session = db_session or self.db_session
        if not session:
            logger.warning("No database session provided for service validation")
            return True, None  # Skip validation if no DB session
        
        try:
            # Use DataAPIClient to fetch entity metadata
            from ...clients.data_api_client import DataAPIClient
            
            data_api_client = DataAPIClient()
            entity_metadata = await data_api_client.get_entity_metadata(entity_id)
            
            if not entity_metadata:
                return False, f"Entity {entity_id} not found in database"
            
            # Check if service is in available_services
            available_services = entity_metadata.get('available_services', [])
            if available_services:
                if isinstance(available_services, list):
                    if service not in available_services:
                        return False, (
                            f"Service {service} not available for {entity_id}. "
                            f"Available: {', '.join(available_services)}"
                        )
                else:
                    logger.warning(f"Entity {entity_id} has invalid available_services format")
            
            # Validate service parameters against capabilities
            domain = service.split('.')[0] if '.' in service else service
            service_name = service.split('.')[1] if '.' in service else service
            
            # Validate service parameters based on domain and capabilities
            if domain == 'light' and service_name == 'turn_on':
                # Check if brightness/color parameters are valid for entity capabilities
                if entity.capabilities:
                    capabilities_list = entity.capabilities if isinstance(entity.capabilities, list) else []
                    # Note: Parameter validation would happen during YAML generation
                    # This is just a basic check that the service is available
                    pass
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error validating service call {service} for {entity_id}: {e}")
            return False, f"Validation error: {str(e)}"
    
    async def validate_service_parameters(
        self,
        entity_id: str,
        service: str,
        parameters: Dict[str, Any],
        db_session: Optional[AsyncSession] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate service parameters against entity capabilities.
        
        Args:
            entity_id: Entity ID
            service: Service call (e.g., "light.turn_on")
            parameters: Service parameters (e.g., {"brightness": 255})
            db_session: Optional database session
        
        Returns:
            (is_valid, error_message)
        """
        session = db_session or self.db_session
        if not session:
            return True, None  # Skip validation if no DB session
        
        try:
            from ...clients.data_api_client import DataAPIClient
            
            data_api_client = DataAPIClient()
            entity_metadata = await data_api_client.get_entity_metadata(entity_id)
            
            if not entity_metadata:
                return False, f"Entity {entity_id} not found"
            
            domain = service.split('.')[0] if '.' in service else service
            capabilities = entity_metadata.get('capabilities', [])
            
            if not isinstance(capabilities, list):
                capabilities = []
            
            # Validate parameters based on domain and capabilities
            if domain == 'light' and service == 'light.turn_on':
                # Check brightness parameter
                if 'brightness' in parameters or 'brightness_pct' in parameters:
                    if 'brightness' not in capabilities:
                        return False, f"Entity {entity_id} does not support brightness control"
                
                # Check color parameters
                if 'rgb_color' in parameters or 'color_name' in parameters:
                    if 'rgb_color' not in capabilities and 'color' not in capabilities:
                        return False, f"Entity {entity_id} does not support color control"
                
                # Check color_temp parameter
                if 'color_temp' in parameters or 'kelvin' in parameters:
                    if 'color_temp' not in capabilities:
                        return False, f"Entity {entity_id} does not support color temperature control"
                
                # Check effect parameter
                if 'effect' in parameters:
                    if 'effect' not in capabilities:
                        return False, f"Entity {entity_id} does not support effects"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error validating service parameters: {e}")
            return False, f"Parameter validation error: {str(e)}"
    
    async def get_available_services(
        self,
        entity_id: str,
        db_session: Optional[AsyncSession] = None
    ) -> List[str]:
        """
        Get available services for an entity.
        
        Args:
            entity_id: Entity ID
            db_session: Optional database session
        
        Returns:
            List of available service calls
        """
        session = db_session or self.db_session
        if not session:
            return []
        
        try:
            from ...clients.data_api_client import DataAPIClient
            
            data_api_client = DataAPIClient()
            entity_metadata = await data_api_client.get_entity_metadata(entity_id)
            
            if entity_metadata:
                available_services = entity_metadata.get('available_services', [])
                if isinstance(available_services, list):
                    return available_services
                else:
                    logger.warning(f"Entity {entity_id} has invalid available_services format")
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting available services for {entity_id}: {e}")
            return []

