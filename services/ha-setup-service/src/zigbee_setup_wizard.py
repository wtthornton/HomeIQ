"""
Zigbee2MQTT Setup Wizard

Guided setup wizard for Zigbee2MQTT configuration and device pairing.
Implements Story 31.2: Zigbee2MQTT Setup Wizard

Context7 Best Practices Applied:
- Async/await for all I/O operations
- Proper exception handling with specific error types
- Pydantic models for data validation
- Step-by-step guided workflow
- Comprehensive error reporting
"""
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

import aiohttp
from pydantic import BaseModel, Field

from .config import get_settings
from .http_client import get_http_session
from .integration_checker import IntegrationHealthChecker, IntegrationStatus

settings = get_settings()
logger = logging.getLogger(__name__)


class SetupStep(str, Enum):
    """Setup wizard steps"""
    PREREQUISITES = "prerequisites"
    MQTT_CONFIG = "mqtt_config"
    ADDON_INSTALL = "addon_install"
    ADDON_CONFIG = "addon_config"
    COORDINATOR_SETUP = "coordinator_setup"
    DEVICE_PAIRING = "device_pairing"
    NETWORK_OPTIMIZATION = "network_optimization"
    VALIDATION = "validation"


class SetupStatus(str, Enum):
    """Setup step status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class DeviceType(str, Enum):
    """Zigbee device types"""
    SWITCH = "switch"
    SENSOR = "sensor"
    LIGHT = "light"
    DIMMER = "dimmer"
    THERMOSTAT = "thermostat"
    DOOR_SENSOR = "door_sensor"
    MOTION_SENSOR = "motion_sensor"
    OTHER = "other"


@dataclass
class SetupStepResult:
    """Result of a setup step"""
    step: SetupStep
    status: SetupStatus
    message: str
    data: dict | None = None
    error: str | None = None
    duration_seconds: float | None = None


@dataclass
class DeviceInfo:
    """Zigbee device information"""
    device_id: str
    friendly_name: str
    device_type: DeviceType
    manufacturer: str | None = None
    model: str | None = None
    signal_strength: int | None = None
    last_seen: datetime | None = None


class SetupWizardRequest(BaseModel):
    """Setup wizard request"""
    coordinator_type: str = Field(..., description="Type of Zigbee coordinator")
    network_channel: int | None = Field(None, description="Zigbee network channel (11-26)")
    pan_id: str | None = Field(None, description="Personal Area Network ID")
    extended_pan_id: str | None = Field(None, description="Extended PAN ID")
    network_key: str | None = Field(None, description="Network security key")


class SetupWizardResponse(BaseModel):
    """Setup wizard response"""
    wizard_id: str
    current_step: SetupStep
    status: SetupStatus
    progress_percentage: float = Field(ge=0, le=100)
    message: str
    steps_completed: list[SetupStep] = Field(default_factory=list)
    steps_failed: list[SetupStep] = Field(default_factory=list)
    estimated_time_remaining_minutes: int | None = None
    recommendations: list[str] = Field(default_factory=list)


class Zigbee2MQTTSetupWizard:
    """
    Comprehensive Zigbee2MQTT setup wizard with guided configuration
    """

    def __init__(self):
        self.ha_url = settings.ha_url.rstrip("/")
        self.ha_token = settings.ha_token
        self.integration_checker = IntegrationHealthChecker()
        self.active_wizards: dict[str, dict] = {}

    async def start_setup_wizard(self, request: SetupWizardRequest) -> SetupWizardResponse:
        """
        Start a new Zigbee2MQTT setup wizard
        
        Args:
            request: Setup wizard configuration request
            
        Returns:
            Initial wizard response with first step
        """
        wizard_id = f"zigbee_setup_{uuid.uuid4().hex[:12]}"

        # Initialize wizard state
        wizard_state = {
            "wizard_id": wizard_id,
            "request": request,
            "current_step": SetupStep.PREREQUISITES,
            "status": SetupStatus.IN_PROGRESS,
            "start_time": datetime.now(timezone.utc),
            "steps_completed": [],
            "steps_failed": [],
            "step_results": {}
        }

        self.active_wizards[wizard_id] = wizard_state

        # Start with prerequisites check
        await self._execute_step(wizard_id, SetupStep.PREREQUISITES)

        return self._create_wizard_response(wizard_id)

    async def continue_wizard(self, wizard_id: str) -> SetupWizardResponse:
        """
        Continue the setup wizard to the next step
        
        Args:
            wizard_id: Wizard identifier
            
        Returns:
            Updated wizard response
        """
        if wizard_id not in self.active_wizards:
            raise ValueError(f"Wizard {wizard_id} not found")

        wizard_state = self.active_wizards[wizard_id]

        # Determine next step
        next_step = self._get_next_step(wizard_state)

        if next_step:
            await self._execute_step(wizard_id, next_step)
        else:
            wizard_state["status"] = SetupStatus.COMPLETED

        return self._create_wizard_response(wizard_id)

    async def _execute_step(self, wizard_id: str, step: SetupStep) -> None:
        """Execute a specific setup step"""
        wizard_state = self.active_wizards[wizard_id]
        start_time = datetime.now(timezone.utc)

        try:
            logger.info(f"Executing step {step} for wizard {wizard_id}")

            # Update wizard state
            wizard_state["current_step"] = step
            wizard_state["status"] = SetupStatus.IN_PROGRESS

            # Execute step-specific logic
            if step == SetupStep.PREREQUISITES:
                result = await self._check_prerequisites()
            elif step == SetupStep.MQTT_CONFIG:
                result = await self._configure_mqtt()
            elif step == SetupStep.ADDON_INSTALL:
                result = await self._install_addon()
            elif step == SetupStep.ADDON_CONFIG:
                result = await self._configure_addon(wizard_state["request"])
            elif step == SetupStep.COORDINATOR_SETUP:
                result = await self._setup_coordinator(wizard_state["request"])
            elif step == SetupStep.DEVICE_PAIRING:
                result = await self._setup_device_pairing()
            elif step == SetupStep.NETWORK_OPTIMIZATION:
                result = await self._optimize_network()
            elif step == SetupStep.VALIDATION:
                result = await self._validate_setup()
            else:
                result = SetupStepResult(
                    step=step,
                    status=SetupStatus.FAILED,
                    message="Unknown step",
                    error="Step not implemented"
                )

            # Calculate duration
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            result.duration_seconds = duration

            # Store result
            wizard_state["step_results"][step] = result

            # Update wizard status based on result
            if result.status == SetupStatus.COMPLETED:
                wizard_state["steps_completed"].append(step)
            elif result.status == SetupStatus.FAILED:
                wizard_state["steps_failed"].append(step)
                wizard_state["status"] = SetupStatus.FAILED

            logger.info(f"Step {step} completed with status {result.status}")

        except Exception as e:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            result = SetupStepResult(
                step=step,
                status=SetupStatus.FAILED,
                message=f"Step execution failed: {str(e)}",
                error=str(e),
                duration_seconds=duration
            )
            wizard_state["step_results"][step] = result
            wizard_state["steps_failed"].append(step)
            wizard_state["status"] = SetupStatus.FAILED
            logger.error(f"Step {step} failed: {e}")

    async def _check_prerequisites(self) -> SetupStepResult:
        """Check system prerequisites for Zigbee2MQTT"""
        try:
            prerequisites = []

            # Check HA authentication
            auth_result = await self.integration_checker.check_ha_authentication()
            if auth_result.status != IntegrationStatus.HEALTHY:
                prerequisites.append("Home Assistant authentication failed")

            # Check MQTT integration
            mqtt_result = await self.integration_checker.check_mqtt_integration()
            if mqtt_result.status == IntegrationStatus.NOT_CONFIGURED:
                prerequisites.append("MQTT integration not configured")
            elif mqtt_result.status == IntegrationStatus.ERROR:
                prerequisites.append("MQTT integration has errors")

            # Check for existing Zigbee2MQTT addon
            z2m_result = await self.integration_checker.check_zigbee2mqtt_integration()
            if z2m_result.status == IntegrationStatus.HEALTHY:
                prerequisites.append("Zigbee2MQTT already configured and working")

            if prerequisites:
                return SetupStepResult(
                    step=SetupStep.PREREQUISITES,
                    status=SetupStatus.COMPLETED,
                    message=f"Prerequisites checked: {', '.join(prerequisites)}",
                    data={"prerequisites": prerequisites}
                )
            else:
                return SetupStepResult(
                    step=SetupStep.PREREQUISITES,
                    status=SetupStatus.COMPLETED,
                    message="All prerequisites satisfied",
                    data={"prerequisites": ["All checks passed"]}
                )

        except Exception as e:
            return SetupStepResult(
                step=SetupStep.PREREQUISITES,
                status=SetupStatus.FAILED,
                message=f"Prerequisites check failed: {str(e)}",
                error=str(e)
            )

    async def _configure_mqtt(self) -> SetupStepResult:
        """Configure MQTT integration"""
        try:
            # Check if MQTT is already configured
            mqtt_result = await self.integration_checker.check_mqtt_integration()

            if mqtt_result.status == IntegrationStatus.HEALTHY:
                return SetupStepResult(
                    step=SetupStep.MQTT_CONFIG,
                    status=SetupStatus.COMPLETED,
                    message="MQTT integration already configured and healthy",
                    data={"mqtt_status": "healthy"}
                )

            # For now, provide guidance for manual configuration
            return SetupStepResult(
                step=SetupStep.MQTT_CONFIG,
                status=SetupStatus.COMPLETED,
                message="MQTT configuration guidance provided",
                data={
                    "mqtt_status": "needs_configuration",
                    "instructions": [
                        "1. Go to Home Assistant → Settings → Devices & Services",
                        "2. Click 'Add Integration' and search for 'MQTT'",
                        "3. Configure MQTT broker settings (typically localhost:1883)",
                        "4. Enable 'Discovery' for automatic device detection"
                    ]
                }
            )

        except Exception as e:
            return SetupStepResult(
                step=SetupStep.MQTT_CONFIG,
                status=SetupStatus.FAILED,
                message=f"MQTT configuration failed: {str(e)}",
                error=str(e)
            )

    async def _install_addon(self) -> SetupStepResult:
        """Install Zigbee2MQTT addon"""
        try:
            # Check if addon is already installed
            session = await get_http_session()
            headers = {
                "Authorization": f"Bearer {self.ha_token}",
                "Content-Type": "application/json"
            }

            # Check addon status
            async with session.get(
                f"{self.ha_url}/api/hassio/addon/zigbee2mqtt/info",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    addon_info = await response.json()
                    if addon_info.get("state") == "started":
                        return SetupStepResult(
                            step=SetupStep.ADDON_INSTALL,
                            status=SetupStatus.COMPLETED,
                            message="Zigbee2MQTT addon already installed and running",
                            data={"addon_state": "running"}
                        )
                    else:
                        # Try to start the addon
                        async with session.post(
                            f"{self.ha_url}/api/hassio/addon/zigbee2mqtt/start",
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=30)
                        ) as start_response:
                            if start_response.status == 200:
                                return SetupStepResult(
                                    step=SetupStep.ADDON_INSTALL,
                                    status=SetupStatus.COMPLETED,
                                    message="Zigbee2MQTT addon started successfully",
                                    data={"addon_state": "started"}
                                )
                            else:
                                return SetupStepResult(
                                    step=SetupStep.ADDON_INSTALL,
                                    status=SetupStatus.FAILED,
                                    message=f"Failed to start addon: HTTP {start_response.status}",
                                    error=f"HTTP {start_response.status}"
                                )
                else:
                    return SetupStepResult(
                        step=SetupStep.ADDON_INSTALL,
                        status=SetupStatus.COMPLETED,
                        message="Addon installation guidance provided",
                        data={
                            "addon_status": "needs_installation",
                            "instructions": [
                                "1. Go to Home Assistant -> Supervisor -> Add-on Store",
                                "2. Search for 'Zigbee2MQTT'",
                                "3. Click 'Install' and wait for installation to complete",
                                "4. Click 'Start' to start the addon"
                            ]
                        }
                    )

        except Exception as e:
            return SetupStepResult(
                step=SetupStep.ADDON_INSTALL,
                status=SetupStatus.FAILED,
                message=f"Addon installation failed: {str(e)}",
                error=str(e)
            )

    async def _configure_addon(self, request: SetupWizardRequest) -> SetupStepResult:
        """Configure Zigbee2MQTT addon settings"""
        try:
            # Get MQTT broker details from integration checker
            mqtt_result = await self.integration_checker.check_mqtt_integration()
            mqtt_broker = "mqtt://localhost:1883"  # Default
            if mqtt_result.check_details:
                broker_host = mqtt_result.check_details.get("broker", "localhost")
                broker_port = mqtt_result.check_details.get("port", 1883)
                mqtt_broker = f"mqtt://{broker_host}:{broker_port}"

            # Determine serial port based on coordinator type
            serial_port = "/dev/ttyUSB0"  # Default
            if "SLZB" in request.coordinator_type.upper():
                # SLZB-06P7 typically uses /dev/ttyUSB0 or /dev/ttyACM0
                # User may need to check actual port in HA Supervisor → System → Hardware
                serial_port = "/dev/ttyUSB0"  # Most common, but may need adjustment

            # Configure addon with provided settings
            config = {
                "data_path": "/config/zigbee2mqtt",
                "homeassistant": True,
                "permit_join": False,
                "mqtt": {
                    "base_topic": "zigbee2mqtt",
                    "server": mqtt_broker
                },
                "serial": {
                    "port": serial_port
                },
                "advanced": {
                    "log_level": "info",
                    "log_output": ["console", "file"]
                }
            }

            # Add network settings if provided
            if request.network_channel:
                config["advanced"]["channel"] = request.network_channel
            if request.pan_id:
                config["advanced"]["pan_id"] = int(request.pan_id, 16)
            if request.extended_pan_id:
                config["advanced"]["extended_pan_id"] = request.extended_pan_id
            if request.network_key:
                config["advanced"]["network_key"] = request.network_key

            # Redact sensitive fields before returning in response
            import copy
            safe_config = copy.deepcopy(config)
            if "advanced" in safe_config and "network_key" in safe_config["advanced"]:
                safe_config["advanced"]["network_key"] = "***REDACTED***"

            return SetupStepResult(
                step=SetupStep.ADDON_CONFIG,
                status=SetupStatus.COMPLETED,
                message="Addon configuration prepared",
                data={
                    "config": safe_config,
                    "instructions": [
                        "1. Go to Zigbee2MQTT addon → Configuration",
                        "2. Replace the configuration with the generated config",
                        "3. Save and restart the addon",
                        "4. Check logs for any configuration errors"
                    ]
                }
            )

        except Exception as e:
            return SetupStepResult(
                step=SetupStep.ADDON_CONFIG,
                status=SetupStatus.FAILED,
                message=f"Addon configuration failed: {str(e)}",
                error=str(e)
            )

    async def _setup_coordinator(self, request: SetupWizardRequest) -> SetupStepResult:
        """Setup Zigbee coordinator"""
        try:
            # Check coordinator connectivity
            session = await get_http_session()
            headers = {
                "Authorization": f"Bearer {self.ha_token}",
                "Content-Type": "application/json"
            }

            # Check for coordinator entity using single-entity endpoint
            async with session.get(
                f"{self.ha_url}/api/states/sensor.zigbee2mqtt_bridge_state",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    coordinator_state = await response.json()

                    if coordinator_state and coordinator_state.get('state') == 'online':
                        return SetupStepResult(
                            step=SetupStep.COORDINATOR_SETUP,
                            status=SetupStatus.COMPLETED,
                            message="Coordinator is online and connected",
                            data={"coordinator_status": "online"}
                        )
                    else:
                        return SetupStepResult(
                            step=SetupStep.COORDINATOR_SETUP,
                            status=SetupStatus.COMPLETED,
                            message="Coordinator setup guidance provided",
                            data={
                                "coordinator_status": "needs_setup",
                                "instructions": [
                                    f"1. Connect your {request.coordinator_type} coordinator",
                                    "2. Check the correct USB port in addon configuration",
                                    "3. Restart the Zigbee2MQTT addon",
                                    "4. Check addon logs for coordinator connection status"
                                ]
                            }
                        )
                else:
                    return SetupStepResult(
                        step=SetupStep.COORDINATOR_SETUP,
                        status=SetupStatus.FAILED,
                        message=f"Failed to check coordinator: HTTP {response.status}",
                        error=f"HTTP {response.status}"
                    )

        except Exception as e:
            return SetupStepResult(
                step=SetupStep.COORDINATOR_SETUP,
                status=SetupStatus.FAILED,
                message=f"Coordinator setup failed: {str(e)}",
                error=str(e)
            )

    async def _setup_device_pairing(self) -> SetupStepResult:
        """Setup device pairing mode"""
        try:
            # Enable permit join for device pairing
            session = await get_http_session()
            headers = {
                "Authorization": f"Bearer {self.ha_token}",
                "Content-Type": "application/json"
            }

            # Enable permit join
            payload = {"value": True}
            async with session.post(
                f"{self.ha_url}/api/services/zigbee2mqtt/permit_join",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                if response.status == 200:
                    return SetupStepResult(
                        step=SetupStep.DEVICE_PAIRING,
                        status=SetupStatus.COMPLETED,
                        message="Device pairing mode enabled",
                        data={
                            "pairing_enabled": True,
                            "instructions": [
                                "1. Put your Zigbee device in pairing mode",
                                "2. Device should appear in Zigbee2MQTT within 60 seconds",
                                "3. Check the Zigbee2MQTT web interface for new devices",
                                "4. Disable permit join after pairing is complete"
                            ]
                        }
                    )
                else:
                    return SetupStepResult(
                        step=SetupStep.DEVICE_PAIRING,
                        status=SetupStatus.COMPLETED,
                        message="Device pairing guidance provided",
                        data={
                            "pairing_enabled": False,
                            "instructions": [
                                "1. Go to Zigbee2MQTT web interface",
                                "2. Click 'Permit join' button",
                                "3. Put your device in pairing mode",
                                "4. Wait for device to appear in the device list"
                            ]
                        }
                    )

        except Exception as e:
            return SetupStepResult(
                step=SetupStep.DEVICE_PAIRING,
                status=SetupStatus.FAILED,
                message=f"Device pairing setup failed: {str(e)}",
                error=str(e)
            )

    async def _optimize_network(self) -> SetupStepResult:
        """Optimize Zigbee network settings"""
        try:
            # Get current network status
            health_status = await self.integration_checker.check_zigbee2mqtt_integration()

            optimization_recommendations = []

            if health_status.check_details.get("device_count", 0) == 0:
                optimization_recommendations.append("No devices found - pair devices first")
            else:
                optimization_recommendations.extend([
                    "Network optimization recommendations:",
                    "• Use channel 25 for best WiFi coexistence",
                    "• Ensure coordinator is centrally located",
                    "• Keep coordinator away from WiFi routers",
                    "• Use repeaters for large networks"
                ])

            return SetupStepResult(
                step=SetupStep.NETWORK_OPTIMIZATION,
                status=SetupStatus.COMPLETED,
                message="Network optimization completed",
                data={
                    "recommendations": optimization_recommendations,
                    "device_count": health_status.check_details.get("device_count", 0)
                }
            )

        except Exception as e:
            return SetupStepResult(
                step=SetupStep.NETWORK_OPTIMIZATION,
                status=SetupStatus.FAILED,
                message=f"Network optimization failed: {str(e)}",
                error=str(e)
            )

    async def _validate_setup(self) -> SetupStepResult:
        """Validate complete Zigbee2MQTT setup"""
        try:
            # Run comprehensive validation
            validation_results = []

            # Check integration health
            z2m_result = await self.integration_checker.check_zigbee2mqtt_integration()
            if z2m_result.status == IntegrationStatus.HEALTHY:
                validation_results.append("✅ Zigbee2MQTT integration healthy")
            else:
                validation_results.append(f"❌ Zigbee2MQTT integration: {z2m_result.status}")

            # Check device count
            device_count = z2m_result.check_details.get("device_count", 0)
            if device_count > 0:
                validation_results.append(f"✅ {device_count} Zigbee devices detected")
            else:
                validation_results.append("⚠️ No Zigbee devices detected")

            # Check bridge state
            bridge_state = z2m_result.check_details.get("bridge_state", "unknown")
            if bridge_state == "online":
                validation_results.append("✅ Bridge is online")
            else:
                validation_results.append(f"❌ Bridge state: {bridge_state}")

            all_healthy = all("✅" in result for result in validation_results)

            return SetupStepResult(
                step=SetupStep.VALIDATION,
                status=SetupStatus.COMPLETED if all_healthy else SetupStatus.FAILED,
                message="Setup validation completed",
                data={
                    "validation_results": validation_results,
                    "all_healthy": all_healthy,
                    "device_count": device_count,
                    "bridge_state": bridge_state
                }
            )

        except Exception as e:
            return SetupStepResult(
                step=SetupStep.VALIDATION,
                status=SetupStatus.FAILED,
                message=f"Setup validation failed: {str(e)}",
                error=str(e)
            )

    def _get_next_step(self, wizard_state: dict) -> SetupStep | None:
        """Determine the next step in the wizard"""
        completed_steps = set(wizard_state["steps_completed"])
        failed_steps = set(wizard_state["steps_failed"])

        # Define step order
        step_order = [
            SetupStep.PREREQUISITES,
            SetupStep.MQTT_CONFIG,
            SetupStep.ADDON_INSTALL,
            SetupStep.ADDON_CONFIG,
            SetupStep.COORDINATOR_SETUP,
            SetupStep.DEVICE_PAIRING,
            SetupStep.NETWORK_OPTIMIZATION,
            SetupStep.VALIDATION
        ]

        # Find next incomplete step
        for step in step_order:
            if step not in completed_steps and step not in failed_steps:
                return step

        return None

    def _create_wizard_response(self, wizard_id: str) -> SetupWizardResponse:
        """Create wizard response from current state"""
        wizard_state = self.active_wizards[wizard_id]

        # Calculate progress
        total_steps = 8
        completed_steps = len(wizard_state["steps_completed"])
        progress = (completed_steps / total_steps) * 100

        # Calculate estimated time remaining
        elapsed_time = datetime.now(timezone.utc) - wizard_state["start_time"]
        if completed_steps > 0:
            avg_time_per_step = elapsed_time.total_seconds() / completed_steps
            remaining_steps = total_steps - completed_steps
            estimated_remaining = (remaining_steps * avg_time_per_step) / 60  # minutes
        else:
            estimated_remaining = None

        # Generate recommendations
        recommendations = []
        if wizard_state["steps_failed"]:
            recommendations.append("Some steps failed - check error messages and retry")
        if wizard_state["status"] == SetupStatus.IN_PROGRESS:
            recommendations.append("Continue with the next step to complete setup")

        return SetupWizardResponse(
            wizard_id=wizard_id,
            current_step=wizard_state["current_step"],
            status=wizard_state["status"],
            progress_percentage=progress,
            message=f"Wizard {wizard_state['status'].value} - Step: {wizard_state['current_step'].value}",
            steps_completed=wizard_state["steps_completed"],
            steps_failed=wizard_state["steps_failed"],
            estimated_time_remaining_minutes=int(estimated_remaining) if estimated_remaining else None,
            recommendations=recommendations
        )

    async def get_wizard_status(self, wizard_id: str) -> SetupWizardResponse | None:
        """Get current wizard status"""
        if wizard_id not in self.active_wizards:
            return None

        return self._create_wizard_response(wizard_id)

    async def cancel_wizard(self, wizard_id: str) -> bool:
        """Cancel an active wizard"""
        if wizard_id in self.active_wizards:
            del self.active_wizards[wizard_id]
            return True
        return False
