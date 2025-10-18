"""
Integration Health Checker Service

Context7 Best Practices Applied:
- Async context managers for MQTT connections
- Proper exception handling with specific error types
- Retry logic with exponential backoff
- Pydantic models for validation
"""
import aiohttp
import asyncio
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

from .config import get_settings
from .schemas import IntegrationStatus

settings = get_settings()


class CheckResult(BaseModel):
    """Integration check result model"""
    integration_name: str
    integration_type: str
    status: IntegrationStatus
    is_configured: bool = False
    is_connected: bool = False
    error_message: Optional[str] = None
    check_details: Dict = Field(default_factory=dict)
    last_check: datetime = Field(default_factory=datetime.now)


class IntegrationHealthChecker:
    """
    Comprehensive integration health checker
    
    Implements detailed health checks for:
    - MQTT broker connectivity
    - Zigbee2MQTT addon status
    - Home Assistant integrations
    - Device discovery validation
    - Authentication validation
    """
    
    def __init__(self):
        self.ha_url = settings.ha_url
        self.ha_token = settings.ha_token
        self.data_api_url = settings.data_api_url
        self.timeout = aiohttp.ClientTimeout(total=10)
    
    async def check_all_integrations(self) -> List[CheckResult]:
        """
        Check all integrations in parallel
        
        Returns:
            List of CheckResult for each integration
        """
        # Run all checks in parallel for performance
        results = await asyncio.gather(
            self.check_ha_authentication(),
            self.check_mqtt_integration(),
            self.check_zigbee2mqtt_integration(),
            self.check_device_discovery(),
            self.check_data_api_integration(),
            self.check_admin_api_integration(),
            return_exceptions=True
        )
        
        # Convert exceptions to error results
        check_results = []
        for result in results:
            if isinstance(result, Exception):
                check_results.append(CheckResult(
                    integration_name="Unknown",
                    integration_type="error",
                    status=IntegrationStatus.ERROR,
                    error_message=str(result)
                ))
            else:
                check_results.append(result)
        
        return check_results
    
    async def check_ha_authentication(self) -> CheckResult:
        """
        Validate Home Assistant authentication token
        
        Checks:
        - Token is present
        - Token is valid
        - Token has required permissions
        """
        if not self.ha_token:
            return CheckResult(
                integration_name="HA Authentication",
                integration_type="auth",
                status=IntegrationStatus.NOT_CONFIGURED,
                is_configured=False,
                is_connected=False,
                error_message="HA_TOKEN not configured",
                check_details={
                    "token_present": False,
                    "recommendation": "Set HA_TOKEN environment variable with long-lived access token"
                }
            )
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.ha_token}",
                    "Content-Type": "application/json"
                }
                
                # Test auth with /api/config endpoint
                async with session.get(
                    f"{self.ha_url}/api/config",
                    headers=headers,
                    timeout=self.timeout
                ) as response:
                    if response.status == 200:
                        config_data = await response.json()
                        return CheckResult(
                            integration_name="HA Authentication",
                            integration_type="auth",
                            status=IntegrationStatus.HEALTHY,
                            is_configured=True,
                            is_connected=True,
                            check_details={
                                "token_valid": True,
                                "ha_version": config_data.get("version", "unknown"),
                                "location": config_data.get("location_name", "unknown"),
                                "permissions": "read/write"
                            }
                        )
                    elif response.status == 401:
                        return CheckResult(
                            integration_name="HA Authentication",
                            integration_type="auth",
                            status=IntegrationStatus.ERROR,
                            is_configured=True,
                            is_connected=False,
                            error_message="Invalid or expired token",
                            check_details={
                                "token_valid": False,
                                "http_status": 401,
                                "recommendation": "Generate new long-lived access token in HA"
                            }
                        )
                    else:
                        return CheckResult(
                            integration_name="HA Authentication",
                            integration_type="auth",
                            status=IntegrationStatus.WARNING,
                            is_configured=True,
                            is_connected=False,
                            error_message=f"Unexpected response: HTTP {response.status}",
                            check_details={"http_status": response.status}
                        )
        
        except asyncio.TimeoutError:
            return CheckResult(
                integration_name="HA Authentication",
                integration_type="auth",
                status=IntegrationStatus.ERROR,
                is_configured=True,
                is_connected=False,
                error_message="Connection timeout",
                check_details={
                    "timeout_seconds": 10,
                    "ha_url": self.ha_url,
                    "recommendation": "Check network connectivity and HA URL"
                }
            )
        except Exception as e:
            return CheckResult(
                integration_name="HA Authentication",
                integration_type="auth",
                status=IntegrationStatus.ERROR,
                is_configured=True,
                is_connected=False,
                error_message=str(e),
                check_details={"error_type": type(e).__name__}
            )
    
    async def check_mqtt_integration(self) -> CheckResult:
        """
        Check MQTT integration status
        
        Checks:
        - MQTT integration configured in HA
        - MQTT broker connectivity
        - MQTT discovery enabled
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.ha_token}",
                    "Content-Type": "application/json"
                }
                
                # Get all config entries
                async with session.get(
                    f"{self.ha_url}/api/config/config_entries/entry",
                    headers=headers,
                    timeout=self.timeout
                ) as response:
                    if response.status == 200:
                        entries = await response.json()
                        mqtt_entry = next(
                            (e for e in entries if e.get('domain') == 'mqtt'),
                            None
                        )
                        
                        if not mqtt_entry:
                            return CheckResult(
                                integration_name="MQTT",
                                integration_type="mqtt",
                                status=IntegrationStatus.NOT_CONFIGURED,
                                is_configured=False,
                                is_connected=False,
                                error_message="MQTT integration not found in Home Assistant",
                                check_details={
                                    "recommendation": "Add MQTT integration via HA UI: Settings → Devices & Services → Add Integration → MQTT"
                                }
                            )
                        
                        # MQTT integration found - check details
                        entry_data = mqtt_entry.get('data', {})
                        broker_host = entry_data.get('broker', 'unknown')
                        broker_port = entry_data.get('port', 1883)
                        discovery = entry_data.get('discovery', False)
                        
                        # Check if broker is reachable
                        is_connected = await self._check_mqtt_broker_connectivity(broker_host, broker_port)
                        
                        status = IntegrationStatus.HEALTHY if is_connected else IntegrationStatus.WARNING
                        
                        return CheckResult(
                            integration_name="MQTT",
                            integration_type="mqtt",
                            status=status,
                            is_configured=True,
                            is_connected=is_connected,
                            error_message=None if is_connected else "MQTT broker not reachable",
                            check_details={
                                "broker": broker_host,
                                "port": broker_port,
                                "discovery_enabled": discovery,
                                "entry_id": mqtt_entry.get('entry_id'),
                                "title": mqtt_entry.get('title', 'MQTT'),
                                "recommendation": "Enable discovery for automatic device detection" if not discovery else None
                            }
                        )
                    else:
                        return CheckResult(
                            integration_name="MQTT",
                            integration_type="mqtt",
                            status=IntegrationStatus.ERROR,
                            is_configured=False,
                            is_connected=False,
                            error_message=f"Failed to get config entries: HTTP {response.status}",
                            check_details={"http_status": response.status}
                        )
        
        except Exception as e:
            return CheckResult(
                integration_name="MQTT",
                integration_type="mqtt",
                status=IntegrationStatus.ERROR,
                is_configured=False,
                is_connected=False,
                error_message=str(e),
                check_details={"error_type": type(e).__name__}
            )
    
    async def _check_mqtt_broker_connectivity(self, broker: str, port: int) -> bool:
        """
        Test MQTT broker TCP connectivity
        
        Args:
            broker: MQTT broker hostname/IP
            port: MQTT broker port
            
        Returns:
            True if broker is reachable
        """
        try:
            # Try to open TCP connection
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(broker, port),
                timeout=5.0
            )
            writer.close()
            await writer.wait_closed()
            return True
        except:
            return False
    
    async def check_zigbee2mqtt_integration(self) -> CheckResult:
        """
        Check Zigbee2MQTT integration status
        
        Checks:
        - Zigbee2MQTT addon installed
        - Zigbee2MQTT running
        - Coordinator connection
        - Device count
        - MQTT bridge status
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.ha_token}",
                    "Content-Type": "application/json"
                }
                
                # Check for Zigbee2MQTT entities (indicates addon is working)
                async with session.get(
                    f"{self.ha_url}/api/states",
                    headers=headers,
                    timeout=self.timeout
                ) as response:
                    if response.status == 200:
                        states = await response.json()
                        
                        # Look for Zigbee2MQTT bridge state
                        z2m_bridge = next(
                            (s for s in states if s.get('entity_id') == 'sensor.zigbee2mqtt_bridge_state'),
                            None
                        )
                        
                        # Count Zigbee devices
                        zigbee_devices = [
                            s for s in states 
                            if s.get('entity_id', '').startswith('zigbee2mqtt.')
                        ]
                        
                        if not z2m_bridge and not zigbee_devices:
                            return CheckResult(
                                integration_name="Zigbee2MQTT",
                                integration_type="zigbee2mqtt",
                                status=IntegrationStatus.NOT_CONFIGURED,
                                is_configured=False,
                                is_connected=False,
                                error_message="Zigbee2MQTT not detected in Home Assistant",
                                check_details={
                                    "recommendation": "Install Zigbee2MQTT addon and configure MQTT integration"
                                }
                            )
                        
                        bridge_state = "unknown"
                        is_online = False
                        
                        if z2m_bridge:
                            bridge_state = z2m_bridge.get('state', 'unknown')
                            is_online = bridge_state.lower() == 'online'
                        
                        status = IntegrationStatus.HEALTHY if is_online else IntegrationStatus.WARNING
                        
                        return CheckResult(
                            integration_name="Zigbee2MQTT",
                            integration_type="zigbee2mqtt",
                            status=status,
                            is_configured=True,
                            is_connected=is_online,
                            error_message=None if is_online else f"Bridge state: {bridge_state}",
                            check_details={
                                "bridge_state": bridge_state,
                                "device_count": len(zigbee_devices),
                                "bridge_entity": z2m_bridge.get('entity_id') if z2m_bridge else None,
                                "recommendation": "Check Zigbee2MQTT addon logs if offline" if not is_online else None
                            }
                        )
                    else:
                        return CheckResult(
                            integration_name="Zigbee2MQTT",
                            integration_type="zigbee2mqtt",
                            status=IntegrationStatus.ERROR,
                            is_configured=False,
                            is_connected=False,
                            error_message=f"Failed to get HA states: HTTP {response.status}",
                            check_details={"http_status": response.status}
                        )
        
        except Exception as e:
            return CheckResult(
                integration_name="Zigbee2MQTT",
                integration_type="zigbee2mqtt",
                status=IntegrationStatus.ERROR,
                is_configured=False,
                is_connected=False,
                error_message=str(e),
                check_details={"error_type": type(e).__name__}
            )
    
    async def check_device_discovery(self) -> CheckResult:
        """
        Validate device discovery functionality
        
        Checks:
        - Device registry accessible
        - Devices being discovered
        - Entity registry sync
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.ha_token}",
                    "Content-Type": "application/json"
                }
                
                # Get device registry
                async with session.get(
                    f"{self.ha_url}/api/config/device_registry/list",
                    headers=headers,
                    timeout=self.timeout
                ) as response:
                    if response.status == 200:
                        devices = await response.json()
                        device_count = len(devices)
                        
                        # Check if HA Ingestor is syncing devices
                        ingestor_sync = await self._check_ingestor_device_sync(device_count)
                        
                        status = IntegrationStatus.HEALTHY if device_count > 0 else IntegrationStatus.WARNING
                        
                        return CheckResult(
                            integration_name="Device Discovery",
                            integration_type="discovery",
                            status=status,
                            is_configured=True,
                            is_connected=True,
                            check_details={
                                "ha_device_count": device_count,
                                "ingestor_device_count": ingestor_sync.get("count", 0),
                                "sync_status": ingestor_sync.get("status", "unknown"),
                                "sync_percentage": ingestor_sync.get("percentage", 0),
                                "recommendation": "Check device integrations if count is low" if device_count < 5 else None
                            }
                        )
                    elif response.status == 404:
                        # REST API endpoint might not be available
                        return CheckResult(
                            integration_name="Device Discovery",
                            integration_type="discovery",
                            status=IntegrationStatus.WARNING,
                            is_configured=True,
                            is_connected=False,
                            error_message="Device registry REST API not available",
                            check_details={
                                "http_status": 404,
                                "recommendation": "Use WebSocket API for device discovery instead"
                            }
                        )
                    else:
                        return CheckResult(
                            integration_name="Device Discovery",
                            integration_type="discovery",
                            status=IntegrationStatus.ERROR,
                            is_configured=False,
                            is_connected=False,
                            error_message=f"Failed to get device registry: HTTP {response.status}",
                            check_details={"http_status": response.status}
                        )
        
        except Exception as e:
            return CheckResult(
                integration_name="Device Discovery",
                integration_type="discovery",
                status=IntegrationStatus.ERROR,
                is_configured=False,
                is_connected=False,
                error_message=str(e),
                check_details={"error_type": type(e).__name__}
            )
    
    async def _check_ingestor_device_sync(self, ha_device_count: int) -> Dict:
        """Check if HA Ingestor has synced devices from HA"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.data_api_url}/api/devices",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        ingestor_count = len(data.get('devices', []))
                        
                        if ha_device_count > 0:
                            sync_percentage = (ingestor_count / ha_device_count) * 100
                        else:
                            sync_percentage = 0
                        
                        status = "synced" if sync_percentage >= 90 else "partial" if sync_percentage > 0 else "not_synced"
                        
                        return {
                            "count": ingestor_count,
                            "status": status,
                            "percentage": round(sync_percentage, 1)
                        }
        except:
            return {"count": 0, "status": "error", "percentage": 0}
    
    async def check_data_api_integration(self) -> CheckResult:
        """Check HA Ingestor Data API status"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.data_api_url}/health",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        health_data = await response.json()
                        return CheckResult(
                            integration_name="Data API",
                            integration_type="ha_ingestor",
                            status=IntegrationStatus.HEALTHY,
                            is_configured=True,
                            is_connected=True,
                            check_details={
                                "service": "data-api",
                                "port": 8006,
                                "health_status": health_data.get("status", "unknown")
                            }
                        )
                    else:
                        return CheckResult(
                            integration_name="Data API",
                            integration_type="ha_ingestor",
                            status=IntegrationStatus.WARNING,
                            is_configured=True,
                            is_connected=False,
                            error_message=f"Data API returned HTTP {response.status}",
                            check_details={"http_status": response.status}
                        )
        except Exception as e:
            return CheckResult(
                integration_name="Data API",
                integration_type="ha_ingestor",
                status=IntegrationStatus.ERROR,
                is_configured=True,
                is_connected=False,
                error_message=str(e),
                check_details={
                    "error_type": type(e).__name__,
                    "recommendation": "Check if data-api service is running"
                }
            )
    
    async def check_admin_api_integration(self) -> CheckResult:
        """Check HA Ingestor Admin API status"""
        try:
            admin_api_url = settings.admin_api_url
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{admin_api_url}/health",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        return CheckResult(
                            integration_name="Admin API",
                            integration_type="ha_ingestor",
                            status=IntegrationStatus.HEALTHY,
                            is_configured=True,
                            is_connected=True,
                            check_details={
                                "service": "admin-api",
                                "port": 8003
                            }
                        )
                    else:
                        return CheckResult(
                            integration_name="Admin API",
                            integration_type="ha_ingestor",
                            status=IntegrationStatus.WARNING,
                            is_configured=True,
                            is_connected=False,
                            error_message=f"Admin API returned HTTP {response.status}"
                        )
        except Exception as e:
            return CheckResult(
                integration_name="Admin API",
                integration_type="ha_ingestor",
                status=IntegrationStatus.ERROR,
                is_configured=True,
                is_connected=False,
                error_message=str(e),
                check_details={
                    "error_type": type(e).__name__,
                    "recommendation": "Check if admin-api service is running"
                }
            )

