"""
Deployment Service

Epic 39, Story 39.10: Automation Service Foundation
Core service for deploying automations to Home Assistant.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..clients.ha_client import HomeAssistantClient
from ..database.models import AutomationVersion, Suggestion
from .yaml_generation_service import YAMLGenerationService

logger = logging.getLogger(__name__)


class DeploymentError(Exception):
    """Base exception for deployment errors."""
    pass


class SafetyValidationError(DeploymentError):
    """Raised when safety validation fails."""
    pass


class DeploymentService:
    """
    Service for deploying automations to Home Assistant.
    
    Features:
    - Deploy automations to Home Assistant
    - Safety validation before deployment
    - Version tracking for rollback
    - Batch deployment support
    """

    def __init__(
        self,
        db: AsyncSession,
        ha_client: HomeAssistantClient,
        yaml_service: YAMLGenerationService
    ):
        """
        Initialize deployment service.
        
        Args:
            db: Database session
            ha_client: Home Assistant client
            yaml_service: YAML generation service
        """
        self.db = db
        self.ha_client = ha_client
        self.yaml_service = yaml_service

    async def deploy_suggestion(
        self,
        suggestion_id: int,
        skip_validation: bool = False,
        force_deploy: bool = False
    ) -> dict[str, Any]:
        """
        Deploy an automation suggestion to Home Assistant.
        
        Args:
            suggestion_id: Suggestion ID to deploy
            skip_validation: Skip status validation (admin only)
            force_deploy: Override safety checks (admin only)
        
        Returns:
            Deployment result dictionary
        
        Raises:
            DeploymentError: If deployment fails
        """
        try:
            # Get suggestion from database
            query = select(Suggestion).where(Suggestion.id == suggestion_id)
            result = await self.db.execute(query)
            suggestion = result.scalar_one_or_none()
            
            if not suggestion:
                raise DeploymentError(f"Suggestion {suggestion_id} not found")
            
            # Validate status (unless skip_validation)
            if not skip_validation:
                if suggestion.status not in ["approved", "deployed"]:
                    raise DeploymentError(
                        f"Suggestion status must be 'approved' or 'deployed', got '{suggestion.status}'"
                    )
            
            # Generate YAML if not present
            if not suggestion.automation_yaml:
                logger.info(f"Generating YAML for suggestion {suggestion_id}")
                yaml_content = await self.yaml_service.generate_automation_yaml(suggestion)
                suggestion.automation_yaml = yaml_content
                await self.db.flush()
            
            # Validate YAML
            is_valid, error = await self.yaml_service.validate_yaml(suggestion.automation_yaml)
            if not is_valid:
                raise DeploymentError(f"Invalid YAML: {error}")
            
            # Safety validation (unless force_deploy)
            if not force_deploy:
                # TODO: Epic 39, Story 39.11 - Integrate with dedicated safety validator service
                # Current: Basic entity validation via YAML service
                # Future: Full safety scoring, risk assessment, compliance checks
                all_valid, invalid_entities = await self.yaml_service.validate_entities(
                    suggestion.automation_yaml
                )
                if not all_valid:
                    raise SafetyValidationError(
                        f"Invalid entities found: {', '.join(invalid_entities)}"
                    )
            
            # Deploy to Home Assistant
            deployment_result = await self.ha_client.deploy_automation(
                suggestion.automation_yaml
            )
            
            if deployment_result.get("status") != "deployed":
                raise DeploymentError(f"Deployment failed: {deployment_result}")
            
            automation_id = deployment_result.get("automation_id")
            if not automation_id:
                raise DeploymentError("Deployment result missing automation_id")
            
            # Get previous version number for this automation
            prev_version_query = select(AutomationVersion).where(
                AutomationVersion.automation_id == automation_id
            ).order_by(AutomationVersion.version_number.desc()).limit(1)
            prev_result = await self.db.execute(prev_version_query)
            prev_version = prev_result.scalar_one_or_none()
            version_number = (prev_version.version_number + 1) if prev_version else 1
            
            # Store version for rollback
            version = AutomationVersion(
                suggestion_id=suggestion.id,
                automation_id=automation_id,
                version_number=version_number,
                automation_yaml=suggestion.automation_yaml,
                safety_score=100,  # TODO: Epic 39, Story 39.11 - Get from safety validator service
                deployed_at=datetime.now(timezone.utc)
            )
            self.db.add(version)
            
            # Update suggestion status
            suggestion.status = "deployed"
            suggestion.automation_id = automation_id
            suggestion.deployed_at = datetime.now(timezone.utc)
            suggestion.updated_at = datetime.now(timezone.utc)
            
            await self.db.commit()
            
            logger.info(f"Successfully deployed suggestion {suggestion_id} as {automation_id}")
            
            return {
                "success": True,
                "message": "Automation deployed successfully",
                "data": {
                    "suggestion_id": suggestion_id,
                    "automation_id": automation_id,
                    "status": "deployed"
                }
            }
            
        except DeploymentError:
            await self.db.rollback()
            raise
        except Exception as e:
            logger.error(f"Failed to deploy suggestion {suggestion_id}: {e}")
            await self.db.rollback()
            raise DeploymentError(f"Deployment failed: {e}")

    async def batch_deploy(
        self,
        suggestion_ids: list[int]
    ) -> dict[str, Any]:
        """
        Deploy multiple automations in batch.
        
        Args:
            suggestion_ids: List of suggestion IDs to deploy
        
        Returns:
            Batch deployment result dictionary
        """
        results = {
            "successful": [],
            "failed": [],
            "total": len(suggestion_ids)
        }
        
        for suggestion_id in suggestion_ids:
            try:
                result = await self.deploy_suggestion(suggestion_id)
                results["successful"].append({
                    "suggestion_id": suggestion_id,
                    "automation_id": result["data"]["automation_id"]
                })
            except Exception as e:
                logger.error(f"Failed to deploy suggestion {suggestion_id}: {e}")
                results["failed"].append({
                    "suggestion_id": suggestion_id,
                    "error": str(e)
                })
        
        return results

    async def get_automation_status(
        self,
        automation_id: str
    ) -> dict[str, Any] | None:
        """
        Get status of a deployed automation.
        
        Args:
            automation_id: Home Assistant automation ID
        
        Returns:
            Automation status dictionary or None if not found
        """
        try:
            automation = await self.ha_client.get_automation(automation_id)
            return automation
        except Exception as e:
            logger.error(f"Failed to get automation status: {e}")
            return None

    async def list_deployed_automations(self) -> list[dict[str, Any]]:
        """
        List all deployed automations.
        
        Returns:
            List of automation dictionaries
        """
        try:
            automations = await self.ha_client.list_automations()
            return automations
        except Exception as e:
            logger.error(f"Failed to list automations: {e}")
            return []

    async def rollback_automation(
        self,
        automation_id: str
    ) -> dict[str, Any]:
        """
        Rollback automation to previous version.
        
        Args:
            automation_id: Home Assistant automation ID
        
        Returns:
            Rollback result dictionary
        """
        try:
            # Get previous version (ordered by version_number for proper rollback)
            query = select(AutomationVersion).where(
                AutomationVersion.automation_id == automation_id
            ).order_by(AutomationVersion.version_number.desc())
            
            result = await self.db.execute(query)
            versions = result.scalars().all()
            
            if len(versions) < 2:
                raise DeploymentError("No previous version found for rollback")
            
            # Get previous version (second in list)
            previous_version = versions[1]
            
            # Get latest version number
            latest_version = versions[0]
            new_version_number = latest_version.version_number + 1
            
            # Deploy previous version
            deployment_result = await self.ha_client.deploy_automation(
                previous_version.automation_yaml
            )
            
            # Store new version
            new_version = AutomationVersion(
                suggestion_id=previous_version.suggestion_id,
                automation_id=automation_id,
                version_number=new_version_number,
                automation_yaml=previous_version.automation_yaml,
                safety_score=previous_version.safety_score,
                deployed_at=datetime.now(timezone.utc)
            )
            self.db.add(new_version)
            await self.db.commit()
            
            return {
                "success": True,
                "message": "Automation rolled back successfully",
                "automation_id": automation_id
            }
            
        except Exception as e:
            logger.error(f"Failed to rollback automation {automation_id}: {e}")
            await self.db.rollback()
            raise DeploymentError(f"Rollback failed: {e}")

    async def get_automation_versions(
        self,
        automation_id: str
    ) -> list[dict[str, Any]]:
        """
        Get version history for an automation.
        
        Args:
            automation_id: Home Assistant automation ID
        
        Returns:
            List of version dictionaries
        """
        try:
            query = select(AutomationVersion).where(
                AutomationVersion.automation_id == automation_id
            ).order_by(AutomationVersion.version_number.desc())
            
            result = await self.db.execute(query)
            versions = result.scalars().all()
            
            return [
                {
                    "id": v.id,
                    "suggestion_id": v.suggestion_id,
                    "automation_id": v.automation_id,
                    "version_number": v.version_number,
                    "safety_score": v.safety_score,
                    "deployed_at": v.deployed_at.isoformat() if v.deployed_at else None,
                    "is_active": v.is_active
                }
                for v in versions
            ]
            
        except Exception as e:
            logger.error(f"Failed to get automation versions: {e}")
            return []

    async def enable_automation(self, automation_id: str) -> bool:
        """
        Enable a deployed automation.
        
        Args:
            automation_id: Home Assistant automation ID
        
        Returns:
            True if successful, False otherwise
        """
        try:
            return await self.ha_client.enable_automation(automation_id)
        except Exception as e:
            logger.error(f"Failed to enable automation {automation_id}: {e}")
            return False

    async def disable_automation(self, automation_id: str) -> bool:
        """
        Disable a deployed automation.
        
        Args:
            automation_id: Home Assistant automation ID
        
        Returns:
            True if successful, False otherwise
        """
        try:
            return await self.ha_client.disable_automation(automation_id)
        except Exception as e:
            logger.error(f"Failed to disable automation {automation_id}: {e}")
            return False

    async def trigger_automation(self, automation_id: str) -> bool:
        """
        Trigger a deployed automation.
        
        Args:
            automation_id: Home Assistant automation ID
        
        Returns:
            True if successful, False otherwise
        """
        try:
            return await self.ha_client.trigger_automation(automation_id)
        except Exception as e:
            logger.error(f"Failed to trigger automation {automation_id}: {e}")
            return False

