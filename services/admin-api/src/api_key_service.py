"""
API Key Management Service
Handles API key configuration and validation for external services
"""

import logging
import os
import re
import asyncio
import aiohttp
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)

class APIKeyStatus(Enum):
    """API key status enumeration"""
    CONFIGURED = "configured"
    INVALID = "invalid"
    REQUIRED = "required"
    DISABLED = "disabled"
    TESTING = "testing"

@dataclass
class APIKeyInfo:
    """API key information model"""
    service: str
    key_name: str
    status: APIKeyStatus
    masked_key: str
    is_required: bool
    description: str
    validation_url: Optional[str] = None

class APIKeyService:
    """API key management service"""
    
    def __init__(self):
        """Initialize API key service"""
        self.config_file = "/app/infrastructure/.env.production"
        self.config_dir = "/app/infrastructure"
        self.allow_secret_writes = os.getenv('ADMIN_API_ALLOW_SECRET_WRITES', 'false').lower() == 'true'
        
        # API key configuration for each service
        self.api_key_config = {
            'weather': {
                'env_var': 'WEATHER_API_KEY',
                'description': 'OpenWeatherMap API Key',
                'required': True,
                'validation_url': 'https://api.openweathermap.org/data/2.5/weather?lat=0&lon=0&appid={key}',
                'validation_response_check': 'cod'
            },
            'carbon-intensity': {
                'env_var': 'WATTTIME_API_TOKEN',
                'description': 'WattTime API Token',
                'required': True,
                'validation_url': 'https://api2.watttime.org/v2/index',
                'validation_response_check': 'status'
            },
            'electricity-pricing': {
                'env_var': 'PRICING_API_KEY',
                'description': 'Electricity Pricing API Key',
                'required': False,
                'validation_url': None,
                'validation_response_check': None
            },
            'air-quality': {
                'env_var': 'AIRNOW_API_KEY',
                'description': 'AirNow API Key',
                'required': True,
                'validation_url': 'https://www.airnowapi.org/aq/observation/zipCode/current/?format=application/json&zipCode=10001&distance=25&API_KEY={key}',
                'validation_response_check': 'Status'
            },
            'calendar': {
                'env_var': 'GOOGLE_CLIENT_SECRET',
                'description': 'Google Calendar API Secret',
                'required': False,
                'validation_url': None,
                'validation_response_check': None
            },
            'smart-meter': {
                'env_var': 'METER_API_TOKEN',
                'description': 'Smart Meter API Token',
                'required': False,
                'validation_url': None,
                'validation_response_check': None
            }
        }
    
    async def get_api_keys(self) -> List[APIKeyInfo]:
        """
        Get current API key status for all services
        
        Returns:
            List of APIKeyInfo objects
        """
        api_keys = []
        
        for service, config in self.api_key_config.items():
            # Get current key value
            current_key = os.getenv(config['env_var'])
            
            # Determine status
            if not current_key:
                status = APIKeyStatus.REQUIRED if config['required'] else APIKeyStatus.DISABLED
            else:
                # Test the key if we have validation
                if config['validation_url']:
                    is_valid = await self._test_api_key(service, current_key)
                    status = APIKeyStatus.CONFIGURED if is_valid else APIKeyStatus.INVALID
                else:
                    status = APIKeyStatus.CONFIGURED
            
            # Create masked key for display
            masked_key = self._mask_api_key(current_key) if current_key else "Not configured"
            
            api_key_info = APIKeyInfo(
                service=service,
                key_name=config['env_var'],
                status=status,
                masked_key=masked_key,
                is_required=config['required'],
                description=config['description'],
                validation_url=config['validation_url']
            )
            
            api_keys.append(api_key_info)
        
        return api_keys
    
    async def update_api_key(self, service: str, api_key: str) -> Tuple[bool, str]:
        """
        Update API key for a service
        
        Args:
            service: Service name
            api_key: New API key value
            
        Returns:
            Tuple of (success, message)
        """
        try:
            if service not in self.api_key_config:
                return False, f"Unknown service: {service}"
            
            config = self.api_key_config[service]
            
            # Validate API key format if needed
            if not self._validate_key_format(service, api_key):
                return False, f"Invalid API key format for {service}"
            
            # Test the API key if validation URL is available
            if config['validation_url']:
                is_valid = await self._test_api_key(service, api_key)
                if not is_valid:
                    return False, f"API key validation failed for {service}"
            
            # Update environment variable
            os.environ[config['env_var']] = api_key
            
            # Update config file
            await self._update_config_file(config['env_var'], api_key)
            
            logger.info(f"Successfully updated API key for {service}")
            return True, f"API key updated successfully for {service}"
            
        except Exception as e:
            logger.error(f"Error updating API key for {service}: {e}")
            return False, f"Error updating API key: {str(e)}"
    
    async def test_api_key(self, service: str, api_key: str) -> Tuple[bool, str]:
        """
        Test an API key without saving it
        
        Args:
            service: Service name
            api_key: API key to test
            
        Returns:
            Tuple of (success, message)
        """
        try:
            if service not in self.api_key_config:
                return False, f"Unknown service: {service}"
            
            config = self.api_key_config[service]
            
            if not config['validation_url']:
                return True, f"No validation available for {service}"
            
            is_valid = await self._test_api_key(service, api_key)
            
            if is_valid:
                return True, f"API key is valid for {service}"
            else:
                return False, f"API key validation failed for {service}"
                
        except Exception as e:
            logger.error(f"Error testing API key for {service}: {e}")
            return False, f"Error testing API key: {str(e)}"
    
    def get_api_key_status(self, service: str) -> APIKeyStatus:
        """
        Get API key status for a specific service
        
        Args:
            service: Service name
            
        Returns:
            APIKeyStatus enum value
        """
        if service not in self.api_key_config:
            return APIKeyStatus.DISABLED
        
        config = self.api_key_config[service]
        current_key = os.getenv(config['env_var'])
        
        if not current_key:
            return APIKeyStatus.REQUIRED if config['required'] else APIKeyStatus.DISABLED
        
        return APIKeyStatus.CONFIGURED
    
    async def _test_api_key(self, service: str, api_key: str) -> bool:
        """
        Test API key validity by making a test request
        
        Args:
            service: Service name
            api_key: API key to test
            
        Returns:
            True if valid, False otherwise
        """
        try:
            config = self.api_key_config[service]
            
            if not config['validation_url']:
                return True  # No validation available, assume valid
            
            # Replace placeholder in validation URL
            test_url = config['validation_url'].format(key=api_key)
            
            # Make test request
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(test_url) as response:
                    if response.status == 200:
                        # Check for expected response structure
                        if config['validation_response_check']:
                            data = await response.json()
                            return config['validation_response_check'] in data
                        return True
                    elif response.status == 401:
                        return False  # Unauthorized - invalid key
                    else:
                        logger.warning(f"Unexpected response status {response.status} for {service}")
                        return False
                        
        except Exception as e:
            logger.error(f"Error testing API key for {service}: {e}")
            return False
    
    def _validate_key_format(self, service: str, api_key: str) -> bool:
        """
        Validate API key format based on service requirements
        
        Args:
            service: Service name
            api_key: API key to validate
            
        Returns:
            True if format is valid, False otherwise
        """
        if not api_key or len(api_key.strip()) == 0:
            return False
        
        # Basic format validation based on service
        if service == 'weather':
            # OpenWeatherMap keys are typically 32 characters
            return len(api_key) >= 20
        elif service == 'carbon-intensity':
            # WattTime tokens are typically longer
            return len(api_key) >= 10
        elif service == 'air-quality':
            # AirNow keys are typically shorter
            return len(api_key) >= 5
        else:
            # Generic validation - at least 5 characters
            return len(api_key) >= 5
    
    def _mask_api_key(self, api_key: str) -> str:
        """
        Mask API key for display purposes
        
        Args:
            api_key: API key to mask
            
        Returns:
            Masked API key string
        """
        if not api_key:
            return "Not configured"
        
        if len(api_key) <= 4:
            return "*" * len(api_key)
        
        # Show first 4 and last 4 characters
        return f"{api_key[:4]}...{api_key[-4:]}"
    
    async def _update_config_file(self, env_var: str, value: str) -> None:
        """
        Update environment variable in config file
        
        Args:
            env_var: Environment variable name
            value: New value
        """
        try:
            if not self.allow_secret_writes:
                raise PermissionError(
                    "Updating stored API keys remotely is disabled. Use infrastructure secrets instead."
                )
            # Read current config file
            config_path = os.path.join(self.config_dir, '.env.production')
            
            if not os.path.exists(config_path):
                # Create config file if it doesn't exist
                os.makedirs(self.config_dir, exist_ok=True)
                lines = []
            else:
                with open(config_path, 'r') as f:
                    lines = f.readlines()
            
            # Update or add the environment variable
            updated = False
            for i, line in enumerate(lines):
                if line.startswith(f"{env_var}="):
                    lines[i] = f"{env_var}={value}\n"
                    updated = True
                    break
            
            if not updated:
                lines.append(f"{env_var}={value}\n")
            
            # Write back to file
            with open(config_path, 'w') as f:
                f.writelines(lines)
            
            logger.info(f"Updated {env_var} in config file")
            
        except Exception as e:
            logger.error(f"Error updating config file: {e}")
            raise
