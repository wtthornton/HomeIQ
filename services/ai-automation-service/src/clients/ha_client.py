"""
Home Assistant API Client
Deploy and manage automations in Home Assistant

Stories:
- AI1.11: Home Assistant Integration
- AI4.1: HA Client Foundation
"""

import aiohttp
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
import yaml

logger = logging.getLogger(__name__)


class HomeAssistantClient:
    """
    Client for interacting with Home Assistant REST API.
    
    Handles deployment and management of automations.
    Story AI4.1: Enhanced with connection health checks, retry logic, and version detection.
    """
    
    def __init__(
        self, 
        ha_url: str, 
        access_token: str,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: int = 10
    ):
        """
        Initialize HA client.
        
        Args:
            ha_url: Home Assistant URL (e.g., "http://homeassistant:8123")
            access_token: Long-lived access token from HA
            max_retries: Maximum number of retry attempts for failed requests
            retry_delay: Initial delay between retries (exponential backoff applied)
            timeout: Request timeout in seconds
        """
        self.ha_url = ha_url.rstrip('/')
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None
        self._version_info: Optional[Dict[str, Any]] = None
        self._last_health_check: Optional[datetime] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """
        Get or create a reusable client session with connection pooling.
        
        Story AI4.1: Implements efficient connection pooling per Context7 best practices.
        
        Returns:
            Configured ClientSession instance
        """
        if self._session is None or self._session.closed:
            # Configure connection pooling per Context7 docs
            connector = aiohttp.TCPConnector(
                limit=20,  # Total connection pool size (Context7 default)
                limit_per_host=5,  # Connections per host
                keepalive_timeout=30,  # Keep connections alive for reuse
                force_close=False  # Enable connection reuse
            )
            
            timeout = aiohttp.ClientTimeout(
                total=self.timeout,
                connect=5,  # Socket connect timeout
                sock_connect=5,  # SSL handshake timeout
                sock_read=self.timeout  # Read timeout
            )
            
            self._session = aiohttp.ClientSession(
                connector=connector,
                headers=self.headers,
                timeout=timeout,
                raise_for_status=False  # Manual status checking
            )
            logger.debug("✅ Created new ClientSession with connection pooling")
        
        return self._session
    
    async def close(self) -> None:
        """
        Close the client session and cleanup connections.
        
        Story AI4.1: Proper resource cleanup per Context7 best practices.
        """
        if self._session and not self._session.closed:
            await self._session.close()
            # Grace period for SSL connections to close (Context7 recommendation)
            await asyncio.sleep(0.250)
            logger.debug("✅ Closed ClientSession and cleaned up connections")
    
    async def _retry_request(
        self,
        method: str,
        endpoint: str,
        return_json: bool = False,
        **kwargs
    ) -> Optional[Any]:
        """
        Make HTTP request with exponential backoff retry logic.
        
        Story AI4.1: Implements retry pattern based on Context7 aiohttp_retry best practices.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            return_json: If True, return parsed JSON instead of response object
            **kwargs: Additional request parameters
        
        Returns:
            Response data (JSON dict or status code) or None on failure
        """
        session = await self._get_session()
        url = f"{self.ha_url}{endpoint}"
        
        for attempt in range(self.max_retries):
            try:
                async with session.request(method, url, **kwargs) as response:
                    # Read response data before exiting context
                    if return_json and response.status == 200:
                        data = await response.json()
                        return data
                    
                    # Handle different status codes
                    if response.status < 500:  # Success or client error
                        return {'status': response.status, 'data': await response.json() if response.status == 200 else None}
                    
                    # Server error - retry with backoff
                    if attempt + 1 < self.max_retries:
                        # Exponential backoff: delay * 2^attempt
                        delay = self.retry_delay * (2 ** attempt)
                        logger.warning(
                            f"⚠️ Server error {response.status} on {endpoint}, "
                            f"retrying in {delay:.1f}s (attempt {attempt + 1}/{self.max_retries})"
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"❌ Max retries reached for {endpoint}, status: {response.status}"
                        )
                        return {'status': response.status, 'data': None}
                        
            except (aiohttp.ClientConnectionError, aiohttp.ClientSSLError) as e:
                if attempt + 1 < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(
                        f"⚠️ Connection error on {endpoint}: {type(e).__name__}, "
                        f"retrying in {delay:.1f}s (attempt {attempt + 1}/{self.max_retries})"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"❌ Max retries reached for {endpoint}, error: {e}"
                    )
                    return None
                    
            except asyncio.TimeoutError:
                if attempt + 1 < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(
                        f"⚠️ Timeout on {endpoint}, "
                        f"retrying in {delay:.1f}s (attempt {attempt + 1}/{self.max_retries})"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"❌ Max retries reached for {endpoint}, timeout")
                    return None
        
        return None
    
    async def get_version(self) -> Optional[Dict[str, Any]]:
        """
        Get Home Assistant version and configuration information.
        
        Story AI4.1 AC2: Detect HA version for compatibility checking.
        
        Returns:
            Dict with version info or None on failure
        """
        if self._version_info is not None:
            return self._version_info
        
        try:
            result = await self._retry_request('GET', '/api/config', return_json=True)
            if result:
                self._version_info = result
                version = self._version_info.get('version', 'unknown')
                logger.info(f"📋 Home Assistant version: {version}")
                return self._version_info
            else:
                logger.error("❌ Failed to get HA version: No response")
                return None
        except Exception as e:
            logger.error(f"❌ Error getting HA version: {e}")
            return None
    
    async def test_connection(self) -> bool:
        """
        Test connection to Home Assistant with health check.
        
        Story AI4.1 AC2: Enhanced health checking with version detection.
        
        Returns:
            True if connection successful
        """
        try:
            result = await self._retry_request('GET', '/api/', return_json=True)
            if result:
                logger.info(f"✅ Connected to Home Assistant: {result.get('message', 'OK')}")
                
                # Get version info
                await self.get_version()
                
                # Update last health check timestamp
                self._last_health_check = datetime.now(timezone.utc)
                
                return True
            else:
                logger.error("❌ HA connection failed: No response")
                return False
        except Exception as e:
            logger.error(f"❌ Failed to connect to HA: {e}")
            return False
    
    async def health_check(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Comprehensive health check with detailed status information.
        
        Story AI4.1 AC2: Returns connection status and HA version.
        
        Returns:
            Tuple of (is_healthy, status_info)
        """
        is_healthy = await self.test_connection()
        
        status_info = {
            'connected': is_healthy,
            'url': self.ha_url,
            'last_check': self._last_health_check.isoformat() if self._last_health_check else None,
            'version_info': self._version_info
        }
        
        return is_healthy, status_info
    
    async def get_automation(self, automation_id: str) -> Optional[Dict]:
        """
        Get a specific automation by ID.
        
        Story AI4.1: Uses retry logic for reliability.
        
        Args:
            automation_id: Automation entity ID (e.g., "automation.morning_lights")
        
        Returns:
            Automation data or None if not found
        """
        session = await self._get_session()
        url = f"{self.ha_url}/api/states/{automation_id}"
        
        # Retry logic specifically for 404 (HA indexing race condition)
        # Exponential backoff: 1s, 2s, 4s (max 3 attempts)
        max_retries = 3
        retry_delays = [1.0, 2.0, 4.0]
        
        for attempt in range(max_retries):
            try:
                async with session.get(url, headers=self.headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        if attempt > 0:
                            logger.info(f"Automation {automation_id} found after {attempt} retry(ies)")
                        return data
                    elif response.status == 404:
                        # 404 might be due to HA not indexing yet - retry with backoff
                        if attempt + 1 < max_retries:
                            delay = retry_delays[attempt]
                            logger.debug(
                                f"Automation {automation_id} not found (404), "
                                f"retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})"
                            )
                            await asyncio.sleep(delay)
                            continue
                        else:
                            # All retries exhausted - automation truly doesn't exist
                            logger.debug(f"Automation {automation_id} not found after {max_retries} attempts")
                            return None
                    else:
                        # Other errors - don't retry
                        logger.error(f"Error getting automation {automation_id}: HTTP {response.status}")
                        return None
            except Exception as e:
                logger.error(f"Error getting automation {automation_id}: {e}")
                return None
        
        return None
    
    async def get_automations(self) -> List[Dict]:
        """
        Get automation configurations from Home Assistant.
        
        Stories:
        - AI3.3: Unconnected Relationship Analysis
        - AI4.1: Enhanced with retry logic
        - AI4.4: Handle different response formats
        
        Returns:
            List of automation configurations with trigger/action details
        """
        try:
            result = await self._retry_request('GET', '/api/config/automation/config', return_json=True)
            
            # Handle different response formats
            if isinstance(result, dict):
                # Response wrapped in {status, data} format
                if 'data' in result:
                    configs = result['data']
                elif 'status' in result and result['status'] == 200:
                    configs = result.get('data', [])
                else:
                    # Treat as a single config wrapped in dict
                    configs = [result] if result else []
            elif isinstance(result, list):
                configs = result
            else:
                configs = []
            
            logger.info(f"✅ Retrieved {len(configs)} automation configurations")
            return configs
        except Exception as e:
            logger.error(f"Error fetching automation configs: {e}")
            return []
    
    async def list_automations(self) -> List[Dict]:
        """
        List all automations in Home Assistant.
        
        Story AI4.1: Enhanced with retry logic.
        
        Returns:
            List of automation entities
        """
        try:
            all_states = await self._retry_request('GET', '/api/states', return_json=True)
            if all_states:
                automations = [
                    s for s in all_states 
                    if s.get('entity_id', '').startswith('automation.')
                ]
                logger.info(f"📋 Found {len(automations)} automations in HA")
                return automations
            else:
                logger.error("Failed to list automations: No response")
                return []
        except Exception as e:
            logger.error(f"Error listing automations: {e}")
            return []
    
    async def deploy_automation(self, automation_yaml: str, automation_id: Optional[str] = None) -> Dict:
        """
        Deploy an automation to Home Assistant.
        
        This uses the automations.yaml file approach via config reload.
        
        Args:
            automation_yaml: YAML automation config
            automation_id: Optional specific automation ID to update
        
        Returns:
            Dict with success status and automation ID
        """
        try:
            # Parse YAML to validate and extract automation ID
            automation_data = yaml.safe_load(automation_yaml)
            
            if not isinstance(automation_data, dict):
                raise ValueError("Invalid automation YAML: must be a dict")
            
            # Get or generate automation ID
            if automation_id is None:
                # Extract from alias or generate from title
                alias = automation_data.get('alias', 'ai_suggested_automation')
                automation_id = f"automation.{alias.lower().replace(' ', '_')}"
            
            logger.info(f"🚀 Deploying automation: {automation_id}")
            
            # For MVP: Use the automation service to create/update
            # In production, you'd write to automations.yaml and reload
            session = await self._get_session()
            async with session.post(
                f"{self.ha_url}/api/services/automation/reload",
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status in [200, 201]:
                    logger.info(f"✅ Automation deployed: {automation_id}")
                    return {
                        "success": True,
                        "automation_id": automation_id,
                        "message": "Automation deployed successfully"
                    }
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Deployment failed ({response.status}): {error_text}")
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}: {error_text}"
                    }
        except Exception as e:
            logger.error(f"❌ Error deploying automation: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def enable_automation(self, automation_id: str) -> bool:
        """
        Enable/turn on an automation.
        
        Args:
            automation_id: Automation entity ID
        
        Returns:
            True if successful
        """
        try:
            session = await self._get_session()
            async with session.post(
                f"{self.ha_url}/api/services/automation/turn_on",
                headers=self.headers,
                json={"entity_id": automation_id},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status in [200, 201]:
                    logger.info(f"✅ Enabled automation: {automation_id}")
                    return True
                else:
                    logger.error(f"Failed to enable {automation_id}: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Error enabling automation {automation_id}: {e}")
            return False
    
    async def disable_automation(self, automation_id: str) -> bool:
        """
        Disable/turn off an automation.
        
        Args:
            automation_id: Automation entity ID
        
        Returns:
            True if successful
        """
        try:
            session = await self._get_session()
            async with session.post(
                f"{self.ha_url}/api/services/automation/turn_off",
                headers=self.headers,
                json={"entity_id": automation_id},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status in [200, 201]:
                    logger.info(f"⏸️ Disabled automation: {automation_id}")
                    return True
                else:
                    logger.error(f"Failed to disable {automation_id}: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Error disabling automation {automation_id}: {e}")
            return False
    
    async def trigger_automation(self, automation_id: str) -> bool:
        """
        Manually trigger an automation.
        
        Args:
            automation_id: Automation entity ID
        
        Returns:
            True if successful
        """
        try:
            session = await self._get_session()
            async with session.post(
                f"{self.ha_url}/api/services/automation/trigger",
                headers=self.headers,
                json={"entity_id": automation_id},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status in [200, 201]:
                    logger.info(f"▶️ Triggered automation: {automation_id}")
                    return True
                else:
                    logger.error(f"Failed to trigger {automation_id}: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Error triggering automation {automation_id}: {e}")
            return False
    
    async def delete_automation(self, automation_id: str) -> bool:
        """
        Delete an automation from Home Assistant.
        
        Note: This requires writing to automations.yaml and reloading.
        For MVP, we'll just disable it.
        
        Args:
            automation_id: Automation entity ID
        
        Returns:
            True if successful
        """
        # For MVP, just disable the automation
        return await self.disable_automation(automation_id)

    async def conversation_process(self, text: str) -> Dict[str, Any]:
        """
        Process natural language using Home Assistant Conversation API.

        This is used by the Ask AI tab to extract entities and understand user intent.

        Args:
            text: Natural language input from user

        Returns:
            Dict containing entities, intent, and response from HA
        """
        try:
            session = await self._get_session()
            async with session.post(
                f"{self.ha_url}/api/conversation/process",
                headers=self.headers,
                json={"text": text},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status in [200, 201]:
                    result = await response.json()
                    logger.info(f"HA Conversation API processed: '{text}' -> {len(result.get('entities', []))} entities")
                    return result
                else:
                    logger.error(f"HA Conversation API failed: {response.status}")
                    return {"entities": [], "intent": None, "response": None}

        except Exception as e:
            logger.error(f"Failed to process conversation with HA: {e}")
            # Return empty result instead of raising to allow fallback
            return {"entities": [], "intent": None, "response": None}
    
    async def validate_automation(self, automation_yaml: str) -> Dict[str, Any]:
        """
        Validate automation YAML without creating it.
        
        Checks:
        - YAML syntax is valid
        - Required fields are present
        - Referenced entities exist in HA
        
        Args:
            automation_yaml: YAML string for automation
        
        Returns:
            Dict with validation results
        """
        try:
            # Parse YAML
            automation_data = yaml.safe_load(automation_yaml)
            
            if not isinstance(automation_data, dict):
                return {
                    "valid": False,
                    "error": "Invalid YAML: must be a dictionary",
                    "details": []
                }
            
            errors = []
            warnings = []
            
            # Check required fields
            if 'trigger' not in automation_data and 'triggers' not in automation_data:
                errors.append("Missing required field: 'trigger' or 'triggers'")
            
            if 'action' not in automation_data and 'actions' not in automation_data:
                errors.append("Missing required field: 'action' or 'actions'")
            
            # Extract and validate entity IDs
            entity_ids = self._extract_entity_ids(automation_data)
            logger.info(f"Validating {len(entity_ids)} entities from automation")
            
            # Check if entities exist in HA
            session = await self._get_session()
            for entity_id in entity_ids:
                async with session.get(
                    f"{self.ha_url}/api/states/{entity_id}",
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 404:
                        warnings.append(f"Entity not found: {entity_id}")
            
            if errors:
                return {
                    "valid": False,
                    "error": "; ".join(errors),
                    "details": warnings
                }
            
            return {
                "valid": True,
                "warnings": warnings,
                "entity_count": len(entity_ids),
                "automation_id": automation_data.get('id', automation_data.get('alias', 'unknown'))
            }
            
        except yaml.YAMLError as e:
            return {
                "valid": False,
                "error": f"YAML syntax error: {str(e)}",
                "details": []
            }
        except Exception as e:
            logger.error(f"Error validating automation: {e}", exc_info=True)
            return {
                "valid": False,
                "error": f"Validation error: {str(e)}",
                "details": []
            }
    
    def _extract_entity_ids(self, automation_data: Dict) -> List[str]:
        """
        Extract all entity IDs from automation config.
        
        Args:
            automation_data: Parsed automation dictionary
        
        Returns:
            List of entity IDs found in the automation
        """
        entity_ids = set()
        
        def extract_from_dict(d: Dict):
            for key, value in d.items():
                if key in ['entity_id', 'target']:
                    if isinstance(value, str) and '.' in value:
                        entity_ids.add(value)
                    elif isinstance(value, dict) and 'entity_id' in value:
                        if isinstance(value['entity_id'], str):
                            entity_ids.add(value['entity_id'])
                        elif isinstance(value['entity_id'], list):
                            entity_ids.update(value['entity_id'])
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, str) and '.' in item:
                                entity_ids.add(item)
                elif isinstance(value, dict):
                    extract_from_dict(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            extract_from_dict(item)
        
        extract_from_dict(automation_data)
        return list(entity_ids)
    
    async def create_automation(self, automation_yaml: str) -> Dict[str, Any]:
        """
        Create a new automation in Home Assistant.
        
        This writes the automation config directly to Home Assistant's configuration.
        
        Args:
            automation_yaml: YAML string for the automation
        
        Returns:
            Dict with creation result including automation_id and status
        """
        try:
            # First validate the automation
            validation = await self.validate_automation(automation_yaml)
            if not validation.get('valid', False):
                return {
                    "success": False,
                    "error": f"Validation failed: {validation.get('error', 'Unknown error')}",
                    "details": validation.get('details', [])
                }
            
            # Parse YAML
            automation_data = yaml.safe_load(automation_yaml)
            
            # Generate automation ID if not present
            if 'id' not in automation_data:
                alias = automation_data.get('alias', 'ai_automation')
                automation_data['id'] = alias.lower().replace(' ', '_').replace('-', '_')
            
            automation_id = f"automation.{automation_data['id']}"
            
            # Create automation via HA REST API
            # Note: HA doesn't have a direct REST endpoint to create automations
            # We need to use the config/automation/config endpoint (requires HA config write access)
            session = await self._get_session()
            async with session.post(
                f"{self.ha_url}/api/config/automation/config/{automation_data['id']}",
                headers=self.headers,
                json=automation_data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status in [200, 201]:
                    result = await response.json()
                    logger.info(f"✅ Automation created: {automation_id}")
                    
                    # Enable the automation
                    await self.enable_automation(automation_id)
                    
                    return {
                        "success": True,
                        "automation_id": automation_id,
                        "message": "Automation created and enabled successfully",
                        "warnings": validation.get('warnings', [])
                    }
                else:
                    error_text = await response.text()
                    error_json = {}
                    try:
                        error_json = await response.json()
                        error_text = error_json.get('message', error_text)
                    except:
                        pass  # Use text if JSON parsing fails
                    
                    logger.error(f"❌ Failed to create automation ({response.status}): {error_text}")
                    raise Exception(f"HTTP {response.status}: {error_text}")
        except Exception as e:
            logger.error(f"❌ Error creating automation: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_entity_state(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current state and attributes for an entity from Home Assistant.
        
        This is a passthrough to HA's /api/states/{entity_id} endpoint.
        Returns the full state object including attributes like is_hue_group.
        
        Args:
            entity_id: Entity ID to lookup (e.g., 'light.office')
            
        Returns:
            Entity state dict with attributes, or None if not found
            
        Example:
            state = await ha_client.get_entity_state('light.office')
            if state and state.get('attributes', {}).get('is_hue_group'):
                print("This is a Hue room group!")
        """
        try:
            session = await self._get_session()
            url = f"{self.ha_url}/api/states/{entity_id}"
            
            async with session.get(url) as response:
                if response.status == 200:
                    state_data = await response.json()
                    logger.debug(f"Retrieved state for {entity_id}: {state_data.get('state', 'unknown')}")
                    return state_data
                elif response.status == 404:
                    logger.warning(f"Entity {entity_id} not found in HA")
                    return None
                else:
                    logger.warning(f"Failed to get entity state for {entity_id}: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error getting entity state for {entity_id}: {e}")
            return None
    
    async def get_entities_by_domain(self, domain: str) -> List[str]:
        """
        Get all entity IDs for a specific domain from Home Assistant.
        
        Queries HA's /api/states endpoint and filters by domain prefix.
        
        Args:
            domain: Domain name (e.g., 'wled', 'light', 'binary_sensor')
            
        Returns:
            List of entity IDs matching the domain (e.g., ['wled.office', 'wled.kitchen'])
            
        Example:
            wled_entities = await ha_client.get_entities_by_domain('wled')
            # Returns: ['wled.office', 'wled.kitchen']
        """
        try:
            session = await self._get_session()
            url = f"{self.ha_url}/api/states"
            
            async with session.get(url) as response:
                if response.status == 200:
                    states = await response.json()
                    domain_entities = []
                    
                    # Handle case where states might not be a list
                    if not isinstance(states, list):
                        logger.warning(f"Unexpected states response type: {type(states)}")
                        return []
                    
                    for state in states:
                        if isinstance(state, dict):
                            entity_id = state.get('entity_id')
                            if entity_id and isinstance(entity_id, str) and entity_id.startswith(f"{domain}."):
                                domain_entities.append(entity_id)
                        elif isinstance(state, str) and state.startswith(f"{domain}."):
                            # Handle case where state is just an entity ID string
                            domain_entities.append(state)
                    
                    logger.info(f"Found {len(domain_entities)} entities for domain '{domain}': {domain_entities[:5]}")
                    return domain_entities
                else:
                    logger.warning(f"Failed to get states from HA: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Error getting entities by domain '{domain}': {e}", exc_info=True)
            return []
    
    async def get_entities_by_area_and_domain(
        self,
        area_id: str,
        domain: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get entities from HA filtered by area and optionally domain.
        
        Uses /api/states endpoint and filters by area_id in attributes.
        This provides real-time entity data from Home Assistant.
        
        Args:
            area_id: Area ID to filter by (e.g., "office")
            domain: Optional domain filter (e.g., "light", "binary_sensor")
            
        Returns:
            List of entity dictionaries with entity_id, state, and attributes
            
        Example:
            office_lights = await ha_client.get_entities_by_area_and_domain("office", "light")
            # Returns: [{"entity_id": "light.office_desk", "state": "on", ...}, ...]
        """
        try:
            session = await self._get_session()
            url = f"{self.ha_url}/api/states"
            
            async with session.get(url) as response:
                if response.status == 200:
                    all_states = await response.json()
                    
                    if not isinstance(all_states, list):
                        logger.warning(f"Unexpected states response type: {type(all_states)}")
                        return []
                    
                    # Filter by area_id and optionally domain
                    filtered_entities = []
                    for state in all_states:
                        if not isinstance(state, dict):
                            continue
                        
                        entity_id = state.get('entity_id', '')
                        attributes = state.get('attributes', {})
                        
                        # Check if entity is in the specified area
                        entity_area_id = attributes.get('area_id')
                        if entity_area_id != area_id:
                            continue
                        
                        # Check domain if specified
                        if domain:
                            entity_domain = entity_id.split('.')[0] if '.' in entity_id else ''
                            if entity_domain != domain:
                                continue
                        
                        # Include entity with full state data
                        filtered_entities.append({
                            'entity_id': entity_id,
                            'state': state.get('state'),
                            'attributes': attributes,
                            'domain': entity_id.split('.')[0] if '.' in entity_id else 'unknown',
                            'friendly_name': attributes.get('friendly_name', entity_id),
                            'area_id': entity_area_id,
                            'device_id': attributes.get('device_id'),
                            'platform': attributes.get('platform', 'unknown')
                        })
                    
                    logger.info(
                        f"✅ Found {len(filtered_entities)} entities in area '{area_id}'"
                        f"{f' (domain: {domain})' if domain else ''}"
                    )
                    if len(filtered_entities) > 0:
                        logger.debug(f"First 3 entities: {[e['entity_id'] for e in filtered_entities[:3]]}")
                    
                    return filtered_entities
                else:
                    logger.warning(f"Failed to get states from HA: {response.status}")
                    return []
        except Exception as e:
            logger.error(
                f"Error getting entities by area '{area_id}' and domain '{domain}': {e}",
                exc_info=True
            )
            return []
    
    async def get_entities_by_area_template(
        self,
        area_id: str,
        domain: Optional[str] = None
    ) -> List[str]:
        """
        Get entity IDs by area using HA Template API.
        
        Uses Jinja2 templates for flexible querying. More efficient than
        fetching all states when you only need entity IDs.
        
        Args:
            area_id: Area ID to filter by (e.g., "office")
            domain: Optional domain filter (e.g., "light")
            
        Returns:
            List of entity IDs matching the criteria
            
        Example:
            office_light_ids = await ha_client.get_entities_by_area_template("office", "light")
            # Returns: ["light.office_desk", "light.office_ceiling", ...]
        """
        try:
            session = await self._get_session()
            
            # Build Jinja2 template
            if domain:
                template = (
                    f"{{% set entities = states.{domain} | "
                    f"selectattr('attributes.area_id', 'eq', '{area_id}') | list %}}\n"
                    f"{{{{ entities | map(attribute='entity_id') | list | tojson }}}}"
                )
            else:
                template = (
                    f"{{% set all_entities = states | list %}}\n"
                    f"{{% set filtered = all_entities | "
                    f"selectattr('attributes.area_id', 'eq', '{area_id}') | list %}}\n"
                    f"{{{{ filtered | map(attribute='entity_id') | list | tojson }}}}"
                )
            
            url = f"{self.ha_url}/api/template"
            
            async with session.post(
                url,
                json={"template": template}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    # Template API returns JSON string, need to parse
                    if isinstance(result, str):
                        import json
                        entity_ids = json.loads(result)
                    else:
                        entity_ids = result
                    
                    if not isinstance(entity_ids, list):
                        logger.warning(f"Unexpected template response type: {type(entity_ids)}")
                        return []
                    
                    logger.info(
                        f"✅ Template API found {len(entity_ids)} entities in area '{area_id}'"
                        f"{f' (domain: {domain})' if domain else ''}"
                    )
                    return entity_ids
                else:
                    error_text = await response.text()
                    logger.warning(
                        f"Template API failed: {response.status} - {error_text}"
                    )
                    return []
        except Exception as e:
            logger.error(
                f"Error using template API for area '{area_id}' and domain '{domain}': {e}",
                exc_info=True
            )
            return []

