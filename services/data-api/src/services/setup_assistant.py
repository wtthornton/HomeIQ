"""
Setup Assistant Service
Phase 2.3: Setup guides and issue detection
"""

import logging
import os
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class SetupAssistantService:
    """Service for device setup assistance"""

    def __init__(self):
        """Initialize setup assistant service"""
        self.ha_url = os.getenv("HA_URL") or os.getenv("HA_HTTP_URL")
        self.ha_token = os.getenv("HA_TOKEN") or os.getenv("HOME_ASSISTANT_TOKEN")
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HA API session"""
        if self._session is None or self._session.closed:
            headers = {
                "Authorization": f"Bearer {self.ha_token}",
                "Content-Type": "application/json"
            }
            timeout = aiohttp.ClientTimeout(total=10)
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=timeout,
                raise_for_status=False
            )
        return self._session

    def generate_setup_guide(
        self,
        device_id: str,
        device_name: str,
        device_type: str | None,
        integration: str | None,
        setup_instructions_url: str | None = None
    ) -> dict[str, Any]:
        """
        Generate setup guide for a device.
        
        Args:
            device_id: Device identifier
            device_name: Device name
            device_type: Device type
            integration: Integration name
            setup_instructions_url: External setup guide URL
            
        Returns:
            Setup guide dictionary
        """
        # Import setup guide generator
        try:
            import sys
            sys.path.append(os.path.join(os.path.dirname(__file__), '../../../device-setup-assistant/src'))
            from setup_guide_generator import SetupGuideGenerator
            
            generator = SetupGuideGenerator()
            return generator.generate_setup_guide(
                device_id=device_id,
                device_name=device_name,
                device_type=device_type,
                integration=integration,
                setup_instructions_url=setup_instructions_url
            )
        except ImportError:
            # Fallback if setup assistant not available
            return {
                "device_id": device_id,
                "device_name": device_name,
                "steps": [
                    {
                        "step": 1,
                        "title": "Configure Device",
                        "description": f"Configure {device_name} in Home Assistant",
                        "type": "action"
                    }
                ],
                "estimated_time_minutes": 10
            }

    async def detect_setup_issues(
        self,
        device_id: str,
        device_name: str,
        entity_ids: list[str]
    ) -> list[dict[str, Any]]:
        """
        Detect setup issues for a device.
        
        Args:
            device_id: Device identifier
            device_name: Device name
            entity_ids: List of entity IDs
            
        Returns:
            List of detected issues
        """
        if not self.ha_url or not self.ha_token:
            return []
        
        try:
            import sys
            sys.path.append(os.path.join(os.path.dirname(__file__), '../../../device-setup-assistant/src'))
            from issue_detector import SetupIssueDetector
            
            detector = SetupIssueDetector(self.ha_url, self.ha_token)
            issues = await detector.detect_setup_issues(
                device_id=device_id,
                device_name=device_name,
                entity_ids=entity_ids
            )
            await detector.close()
            return issues
        except ImportError:
            # Fallback detection
            issues = []
            if not entity_ids:
                issues.append({
                    "type": "no_entities",
                    "severity": "error",
                    "message": f"{device_name} has no entities configured",
                    "solution": "Check device integration configuration"
                })
            return issues


# Singleton instance
_setup_assistant: SetupAssistantService | None = None


def get_setup_assistant() -> SetupAssistantService:
    """Get singleton setup assistant instance"""
    global _setup_assistant
    if _setup_assistant is None:
        _setup_assistant = SetupAssistantService()
    return _setup_assistant

