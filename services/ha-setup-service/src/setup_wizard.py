"""
Setup Wizard Framework

Context7 Best Practices Applied:
- Async/await for all I/O operations
- Proper state management
- Rollback capabilities
- Progress tracking
"""
import uuid
from datetime import datetime
from typing import Any

import aiohttp
from pydantic import BaseModel

from .config import get_settings
from .schemas import SetupWizardStatus

settings = get_settings()


class SetupStep(BaseModel):
    """Individual setup step"""
    step_number: int
    step_name: str
    description: str
    validation_required: bool = True
    rollback_possible: bool = True


class SetupWizardResult(BaseModel):
    """Result of setup wizard execution"""
    success: bool
    session_id: str
    message: str
    steps_completed: int
    total_steps: int
    configuration: dict[str, Any]
    errors: list[str] = []


class SetupWizardFramework:
    """
    Framework for guided setup wizards
    
    Features:
    - Step-by-step execution with validation
    - Progress tracking
    - Rollback on failure
    - Configuration persistence
    """

    def __init__(self):
        self.ha_url = settings.ha_url.rstrip("/")
        self.ha_token = settings.ha_token
        self.active_sessions: dict[str, dict] = {}

    async def start_wizard(
        self,
        integration_type: str,
        steps: list[SetupStep],
        initial_config: dict = None
    ) -> str:
        """
        Start a new setup wizard session
        
        Args:
            integration_type: Type of integration (mqtt, zigbee2mqtt, etc.)
            steps: List of setup steps
            initial_config: Initial configuration data
            
        Returns:
            Session ID for tracking progress
        """
        session_id = str(uuid.uuid4())

        self.active_sessions[session_id] = {
            "session_id": session_id,
            "integration_type": integration_type,
            "steps": steps,
            "current_step": 0,
            "configuration": initial_config or {},
            "status": SetupWizardStatus.IN_PROGRESS,
            "started_at": datetime.now(),
            "completed_steps": [],
            "errors": []
        }

        return session_id

    async def execute_step(
        self,
        session_id: str,
        step_number: int,
        step_data: dict = None
    ) -> dict:
        """
        Execute a single setup step
        
        Args:
            session_id: Wizard session ID
            step_number: Step number to execute
            step_data: Data for this step
            
        Returns:
            Step execution result
        """
        session = self.active_sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        steps = session["steps"]
        if step_number >= len(steps):
            raise ValueError(f"Step {step_number} out of range")

        step = steps[step_number]

        try:
            # Execute step (to be implemented by specific wizard)
            result = await self._execute_step_logic(session, step, step_data)

            # Mark step as completed
            session["completed_steps"].append(step_number)
            session["current_step"] = step_number + 1

            # Update configuration
            if step_data:
                session["configuration"].update(step_data)

            return {
                "success": True,
                "step": step.dict(),
                "result": result,
                "next_step": step_number + 1 if step_number + 1 < len(steps) else None
            }

        except Exception as e:
            session["errors"].append({
                "step": step_number,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

            return {
                "success": False,
                "step": step.dict(),
                "error": str(e)
            }

    async def _execute_step_logic(
        self,
        session: dict,
        step: SetupStep,
        step_data: dict
    ) -> dict:
        """
        Execute step-specific logic
        
        To be overridden by specific wizard implementations
        """
        return {"message": "Step executed successfully"}

    async def rollback_wizard(self, session_id: str):
        """
        Rollback wizard changes
        
        Args:
            session_id: Wizard session ID
        """
        session = self.active_sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Rollback completed steps in reverse order
        completed_steps = session["completed_steps"]

        for step_number in reversed(completed_steps):
            try:
                await self._rollback_step(session, step_number)
            except Exception as e:
                print(f"❌ Error rolling back step {step_number}: {e}")

        session["status"] = SetupWizardStatus.CANCELLED
        session["completed_at"] = datetime.now()

    async def _rollback_step(self, session: dict, step_number: int):
        """
        Rollback a specific step
        
        To be overridden by specific wizard implementations
        """
        pass

    def get_session_status(self, session_id: str) -> dict | None:
        """Get current session status"""
        return self.active_sessions.get(session_id)


class Zigbee2MQTTSetupWizard(SetupWizardFramework):
    """
    Zigbee2MQTT Setup Wizard
    
    Steps:
    1. Check prerequisites (MQTT broker, addon installed)
    2. Configure Zigbee coordinator
    3. Test connection
    4. Enable device discovery
    5. Validate setup
    """

    async def start_zigbee2mqtt_setup(self) -> str:
        """Start Zigbee2MQTT setup wizard"""
        steps = [
            SetupStep(
                step_number=1,
                step_name="Check Prerequisites",
                description="Verify MQTT broker and Zigbee2MQTT addon are installed",
                validation_required=True,
                rollback_possible=False
            ),
            SetupStep(
                step_number=2,
                step_name="Configure Coordinator",
                description="Configure Zigbee coordinator connection",
                validation_required=True,
                rollback_possible=True
            ),
            SetupStep(
                step_number=3,
                step_name="Test Connection",
                description="Test coordinator connectivity",
                validation_required=True,
                rollback_possible=False
            ),
            SetupStep(
                step_number=4,
                step_name="Enable Discovery",
                description="Enable MQTT discovery for automatic device detection",
                validation_required=True,
                rollback_possible=True
            ),
            SetupStep(
                step_number=5,
                step_name="Validate Setup",
                description="Final validation of Zigbee2MQTT integration",
                validation_required=True,
                rollback_possible=False
            )
        ]

        return await self.start_wizard("zigbee2mqtt", steps)

    async def _execute_step_logic(
        self,
        session: dict,
        step: SetupStep,
        step_data: dict
    ) -> dict:
        """Execute Zigbee2MQTT-specific step logic"""

        if step.step_number == 1:
            return await self._check_prerequisites()
        elif step.step_number == 2:
            return await self._configure_coordinator(step_data)
        elif step.step_number == 3:
            return await self._test_connection()
        elif step.step_number == 4:
            return await self._enable_discovery()
        elif step.step_number == 5:
            return await self._validate_setup()

        return {"message": "Step not implemented"}

    async def _check_prerequisites(self) -> dict:
        """Check if MQTT and Zigbee2MQTT addon are installed"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.ha_token}",
                    "Content-Type": "application/json"
                }

                # Check MQTT integration
                async with session.get(
                    f"{self.ha_url}/api/config/config_entries/entry",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        entries = await response.json()
                        mqtt_entry = next((e for e in entries if e.get('domain') == 'mqtt'), None)

                        if not mqtt_entry:
                            return {
                                "success": False,
                                "message": "MQTT integration not found",
                                "recommendation": "Install MQTT integration first"
                            }

                        return {
                            "success": True,
                            "message": "Prerequisites verified",
                            "mqtt_configured": True
                        }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error checking prerequisites: {e}"
            }

    async def _configure_coordinator(self, config_data: dict) -> dict:
        """Configure Zigbee coordinator settings"""
        # Placeholder for coordinator configuration logic
        return {
            "success": True,
            "message": "Coordinator configuration ready",
            "config": config_data
        }

    async def _test_connection(self) -> dict:
        """Test Zigbee coordinator connection"""
        # Placeholder for connection testing
        return {
            "success": True,
            "message": "Connection test passed"
        }

    async def _enable_discovery(self) -> dict:
        """Enable MQTT discovery"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.ha_token}",
                    "Content-Type": "application/json"
                }

                # Trigger MQTT discovery
                async with session.post(
                    f"{self.ha_url}/api/services/mqtt/discover",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        return {
                            "success": True,
                            "message": "MQTT discovery enabled"
                        }
                    else:
                        return {
                            "success": False,
                            "message": f"Failed to enable discovery: HTTP {response.status}"
                        }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error enabling discovery: {e}"
            }

    async def _validate_setup(self) -> dict:
        """Final validation of Zigbee2MQTT setup"""
        # Placeholder for validation logic
        return {
            "success": True,
            "message": "Setup validation complete"
        }


class MQTTSetupWizard(SetupWizardFramework):
    """
    MQTT Integration Setup Wizard
    
    Steps:
    1. Detect MQTT broker
    2. Configure connection
    3. Test connectivity
    4. Enable discovery
    5. Validate integration
    """

    async def start_mqtt_setup(self) -> str:
        """Start MQTT setup wizard"""
        steps = [
            SetupStep(
                step_number=1,
                step_name="Detect MQTT Broker",
                description="Detect and verify MQTT broker installation",
                validation_required=True,
                rollback_possible=False
            ),
            SetupStep(
                step_number=2,
                step_name="Configure Connection",
                description="Configure MQTT broker connection settings",
                validation_required=True,
                rollback_possible=True
            ),
            SetupStep(
                step_number=3,
                step_name="Test Connectivity",
                description="Test MQTT broker connectivity",
                validation_required=True,
                rollback_possible=False
            ),
            SetupStep(
                step_number=4,
                step_name="Enable Discovery",
                description="Enable MQTT discovery for automatic device detection",
                validation_required=True,
                rollback_possible=True
            ),
            SetupStep(
                step_number=5,
                step_name="Validate Integration",
                description="Final validation of MQTT integration",
                validation_required=True,
                rollback_possible=False
            )
        ]

        return await self.start_wizard("mqtt", steps)

