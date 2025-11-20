"""
Automation Deployer

Deploys automations to Home Assistant.
Consolidates deployment logic.

Created: Phase 2 - Core Service Refactoring
"""

import logging
from typing import Any

from ...clients.ha_client import HomeAssistantClient

logger = logging.getLogger(__name__)


class AutomationDeployer:
    """
    Deploys automations to Home Assistant.
    
    Handles deployment, validation, and error recovery.
    """

    def __init__(
        self,
        ha_client: HomeAssistantClient
    ):
        """
        Initialize deployer.
        
        Args:
            ha_client: Home Assistant client for deployment
        """
        self.ha_client = ha_client

        logger.info("AutomationDeployer initialized")

    async def deploy(
        self,
        automation_yaml: str,
        automation_id: str | None = None
    ) -> dict[str, Any]:
        """
        Deploy automation to Home Assistant.
        
        Args:
            automation_yaml: Automation YAML to deploy
            automation_id: Optional automation ID (for updates)
        
        Returns:
            Deployment result dictionary
        """
        try:
            # Use HA client's deployment method
            result = await self.ha_client.create_automation(
                automation_yaml=automation_yaml,
                automation_id=automation_id
            )

            logger.info(f"✅ Automation deployed: {result.get('automation_id', 'unknown')}")
            return result

        except Exception as e:
            logger.error(f"❌ Deployment failed: {e}", exc_info=True)
            raise

