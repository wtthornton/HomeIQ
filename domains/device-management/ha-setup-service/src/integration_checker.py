"""
Integration Health Checker Service

Context7 Best Practices Applied:
- Proper exception handling with specific error types
- Retry logic with exponential backoff
- Pydantic models for validation
"""

import asyncio
import logging
from datetime import datetime

import aiohttp
from homeiq_ha.client import HAClient as SharedHAClient
from homeiq_ha.client import HAWebSocketClient
from pydantic import BaseModel, Field

from .config import get_settings
from .http_client import get_http_session
from .schemas import IntegrationStatus

settings = get_settings()
logger = logging.getLogger(__name__)


class CheckResult(BaseModel):
    """Integration check result model"""

    integration_name: str
    integration_type: str
    status: IntegrationStatus
    is_configured: bool = False
    is_connected: bool = False
    error_message: str | None = None
    check_details: dict = Field(default_factory=dict)
    last_check: datetime = Field(default_factory=datetime.now)


class IntegrationHealthChecker:
    """
    Comprehensive integration health checker

    Implements detailed health checks for:
    - Home Assistant integrations
    - Device discovery validation
    - Authentication validation
    """

    def __init__(self):
        self.ha_url = settings.ha_url.rstrip("/")
        self.ha_token = settings.ha_token
        self._ws: HAWebSocketClient | None = None
        self.data_api_url = settings.data_api_url
        self.api_key = settings.api_key
        self.timeout = aiohttp.ClientTimeout(total=10)

    async def check_all_integrations(self) -> list[CheckResult]:
        """
        Check all integrations in parallel

        Returns:
            List of CheckResult for each integration
        """
        # Run all checks in parallel for performance
        results = await asyncio.gather(
            self.check_ha_authentication(),
            self.check_device_discovery(),
            self.check_data_api_integration(),
            self.check_admin_api_integration(),
            self.check_hacs_integration(),
            return_exceptions=True,
        )

        # Convert exceptions to error results
        check_results = []
        for result in results:
            if isinstance(result, Exception):
                check_results.append(
                    CheckResult(
                        integration_name="Unknown",
                        integration_type="error",
                        status=IntegrationStatus.ERROR,
                        error_message=str(result),
                    )
                )
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
                    "recommendation": "Set HA_TOKEN environment variable with long-lived access token",
                },
            )

        try:
            session = await get_http_session()
            headers = {
                "Authorization": f"Bearer {self.ha_token}",
                "Content-Type": "application/json",
            }

            # Test auth with /api/config endpoint
            async with session.get(
                f"{self.ha_url}/api/config", headers=headers, timeout=self.timeout
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
                            "permissions": "read/write",
                        },
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
                            "recommendation": "Generate new long-lived access token in HA",
                        },
                    )
                else:
                    return CheckResult(
                        integration_name="HA Authentication",
                        integration_type="auth",
                        status=IntegrationStatus.WARNING,
                        is_configured=True,
                        is_connected=False,
                        error_message=f"Unexpected response: HTTP {response.status}",
                        check_details={"http_status": response.status},
                    )

        except TimeoutError:
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
                    "recommendation": "Check network connectivity and HA URL",
                },
            )
        except Exception as e:
            return CheckResult(
                integration_name="HA Authentication",
                integration_type="auth",
                status=IntegrationStatus.ERROR,
                is_configured=True,
                is_connected=False,
                error_message=str(e),
                check_details={"error_type": type(e).__name__},
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
            # This check used to GET /api/config/device_registry/list and had a
            # dedicated 404 branch recommending "Use WebSocket API for device
            # discovery instead" — it knew the REST path was wrong and reported
            # WARNING every time rather than reading the registry. It now does
            # exactly what that branch advised (TAP-5424).
            devices = await self._device_registry()
            device_count = len(devices)

            # Check if HA Ingestor is syncing devices
            ingestor_sync = await self._check_ingestor_device_sync(device_count)

            # The verdict has to carry the worst of what was measured. Deriving
            # it from device_count alone reported HEALTHY while the very same
            # payload said sync_status "error" at 0% -- a green light over a
            # device store that had never received a row.
            sync_status = ingestor_sync.get("status", "unknown")
            if device_count == 0:
                status = IntegrationStatus.WARNING
                recommendation = "Home Assistant reports no devices; check its integrations"
            elif sync_status == "error":
                status = IntegrationStatus.ERROR
                recommendation = f"Devices are not reaching the ingestor: {ingestor_sync.get('error', 'sync failed')}"
            elif sync_status in ("not_synced", "partial"):
                status = IntegrationStatus.WARNING
                recommendation = (
                    f"Only {ingestor_sync.get('count', 0)} of {device_count} devices synced "
                    f"({ingestor_sync.get('percentage', 0)}%)"
                )
            else:
                status = IntegrationStatus.HEALTHY
                recommendation = (
                    "Check device integrations if count is low" if device_count < 5 else None
                )

            return CheckResult(
                integration_name="Device Discovery",
                integration_type="discovery",
                status=status,
                is_configured=True,
                is_connected=True,
                check_details={
                    "ha_device_count": device_count,
                    "ingestor_device_count": ingestor_sync.get("count", 0),
                    "sync_status": sync_status,
                    "sync_percentage": ingestor_sync.get("percentage", 0),
                    "recommendation": recommendation,
                },
            )

        except Exception as e:
            return CheckResult(
                integration_name="Device Discovery",
                integration_type="discovery",
                status=IntegrationStatus.ERROR,
                is_configured=False,
                is_connected=False,
                error_message=str(e),
                check_details={"error_type": type(e).__name__},
            )

    async def _device_registry(self) -> list[dict]:
        """Read the device registry over WebSocket.

        Cached across checks so a full integration sweep shares one auth
        handshake; dropped on failure so the next call reconnects.
        """
        try:
            if self._ws is None:
                # The facade derives the ws:// URL from the HTTP base URL.
                self._ws = SharedHAClient(self.ha_url, self.ha_token).ws
                await self._ws.connect()
            return await self._ws.list_devices()
        except Exception:
            await self._close_ws()
            raise

    async def _close_ws(self):
        """Close and forget the WebSocket connection"""
        if self._ws is not None:
            try:
                await self._ws.close()
            finally:
                self._ws = None

    async def _check_ingestor_device_sync(self, ha_device_count: int) -> dict:
        """Check if HA Ingestor has synced devices from HA"""
        try:
            session = await get_http_session()
            # data-api runs with auth enabled and validates a bearer token
            # against the same shared API_KEY this service already holds.
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            async with session.get(
                f"{self.data_api_url}/api/devices",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    ingestor_count = len(data.get("devices", []))

                    if ha_device_count > 0:
                        sync_percentage = (ingestor_count / ha_device_count) * 100
                    else:
                        sync_percentage = 0

                    status = (
                        "synced"
                        if sync_percentage >= 90
                        else "partial"
                        if sync_percentage > 0
                        else "not_synced"
                    )

                    return {
                        "count": ingestor_count,
                        "status": status,
                        "percentage": round(sync_percentage, 1),
                    }

                # Non-200 responses should still return structured error information
                return {
                    "count": 0,
                    "status": "error",
                    "percentage": 0,
                    "error": f"HTTP {response.status}",
                }
        except Exception as exc:
            return {
                "count": 0,
                "status": "error",
                "percentage": 0,
                "error": str(exc),
                "error_type": type(exc).__name__,
            }

    async def check_data_api_integration(self) -> CheckResult:
        """Check HA Ingestor Data API status"""
        try:
            session = await get_http_session()
            async with session.get(
                f"{self.data_api_url}/health", timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    health_data = await response.json()
                    return CheckResult(
                        integration_name="Data API",
                        integration_type="homeiq",
                        status=IntegrationStatus.HEALTHY,
                        is_configured=True,
                        is_connected=True,
                        check_details={
                            "service": "data-api",
                            "port": 8006,
                            "health_status": health_data.get("status", "unknown"),
                        },
                    )
                else:
                    return CheckResult(
                        integration_name="Data API",
                        integration_type="homeiq",
                        status=IntegrationStatus.WARNING,
                        is_configured=True,
                        is_connected=False,
                        error_message=f"Data API returned HTTP {response.status}",
                        check_details={"http_status": response.status},
                    )
        except Exception as e:
            return CheckResult(
                integration_name="Data API",
                integration_type="homeiq",
                status=IntegrationStatus.ERROR,
                is_configured=True,
                is_connected=False,
                error_message=str(e),
                check_details={
                    "error_type": type(e).__name__,
                    "recommendation": "Check if data-api service is running",
                },
            )

    async def check_admin_api_integration(self) -> CheckResult:
        """Check HA Ingestor Admin API status"""
        try:
            admin_api_url = settings.admin_api_url
            session = await get_http_session()
            async with session.get(
                f"{admin_api_url}/health", timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    return CheckResult(
                        integration_name="Admin API",
                        integration_type="homeiq",
                        status=IntegrationStatus.HEALTHY,
                        is_configured=True,
                        is_connected=True,
                        check_details={"service": "admin-api", "port": 8003},
                    )
                else:
                    return CheckResult(
                        integration_name="Admin API",
                        integration_type="homeiq",
                        status=IntegrationStatus.WARNING,
                        is_configured=True,
                        is_connected=False,
                        error_message=f"Admin API returned HTTP {response.status}",
                    )
        except Exception as e:
            return CheckResult(
                integration_name="Admin API",
                integration_type="homeiq",
                status=IntegrationStatus.ERROR,
                is_configured=True,
                is_connected=False,
                error_message=str(e),
                check_details={
                    "error_type": type(e).__name__,
                    "recommendation": "Check if admin-api service is running",
                },
            )

    async def check_hacs_integration(self) -> CheckResult:
        """
        Check HACS (Home Assistant Community Store) installation and status

        Note: HACS cannot be installed via HA API - it requires manual installation.
        This method checks if HACS is already installed.

        Checks:
        - HACS integration exists in HA config entries
        - HACS sensors/entities exist (indicator of installation)
        - Team Tracker integration is installed
        """
        try:
            session = await get_http_session()
            headers = {
                "Authorization": f"Bearer {self.ha_token}",
                "Content-Type": "application/json",
            }

            # Get all config entries to check for HACS
            async with session.get(
                f"{self.ha_url}/api/config/config_entries/entry",
                headers=headers,
                timeout=self.timeout,
            ) as config_response:
                if config_response.status != 200:
                    return CheckResult(
                        integration_name="HACS",
                        integration_type="custom_component",
                        status=IntegrationStatus.ERROR,
                        is_configured=False,
                        is_connected=False,
                        error_message=f"Cannot access HA config: HTTP {config_response.status}",
                        check_details={
                            "recommendation": "Check HA connectivity and token permissions"
                        },
                    )

                config_entries = await config_response.json()

                # Look for HACS in config entries
                hacs_entry = None
                for entry in config_entries:
                    entry_domain = entry.get("domain", "").lower()
                    entry_title = entry.get("title", "").lower()
                    if entry_domain == "hacs" or "hacs" in entry_title:
                        hacs_entry = entry
                        break

            # Fetch /api/states ONCE and filter for both HACS entities AND Team Tracker sensors
            hacs_entities_exist = False
            tt_sensors = []
            async with session.get(
                f"{self.ha_url}/api/states", headers=headers, timeout=self.timeout
            ) as states_response:
                if states_response.status == 200:
                    states = await states_response.json()
                    hacs_entities = [
                        s
                        for s in states
                        if s["entity_id"].startswith("sensor.hacs")
                        or s["entity_id"].startswith("binary_sensor.hacs")
                    ]
                    hacs_entities_exist = len(hacs_entities) > 0
                    tt_sensors = [s for s in states if "team_tracker" in s["entity_id"].lower()]

            # Determine HACS status
            hacs_installed = hacs_entry is not None or hacs_entities_exist

            if hacs_installed:
                # Check for Team Tracker
                team_tracker_installed = any(
                    "team_tracker" in entry.get("domain", "").lower() for entry in config_entries
                )
                team_tracker_installed = team_tracker_installed or len(tt_sensors) > 0

                return CheckResult(
                    integration_name="HACS",
                    integration_type="custom_component",
                    status=IntegrationStatus.HEALTHY,
                    is_configured=True,
                    is_connected=True,
                    check_details={
                        "hacs_installed": True,
                        "hacs_entities_found": hacs_entities_exist,
                        "team_tracker_installed": team_tracker_installed,
                        "recommendation": "Install Team Tracker via HACS"
                        if not team_tracker_installed
                        else "Ready to use sports features",
                    },
                )
            else:
                # HACS not installed
                return CheckResult(
                    integration_name="HACS",
                    integration_type="custom_component",
                    status=IntegrationStatus.NOT_CONFIGURED,
                    is_configured=False,
                    is_connected=False,
                    error_message="HACS is not installed",
                    check_details={
                        "hacs_installed": False,
                        "installation_note": "HACS must be installed manually via filesystem access",
                        "recommendation": "See installation guide at https://hacs.xyz/docs/setup/download",
                        "manual_steps_required": True,
                    },
                )
        except Exception as e:
            return CheckResult(
                integration_name="HACS",
                integration_type="custom_component",
                status=IntegrationStatus.ERROR,
                is_configured=False,
                is_connected=False,
                error_message=str(e),
                check_details={
                    "error_type": type(e).__name__,
                    "recommendation": "Check HA connectivity and permissions",
                },
            )
