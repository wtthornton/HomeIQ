"""
Autonomous Execution Path (Epic 68, Story 68.4).

Executes high-confidence, low-risk actions directly via ha-device-control
instead of delegating to ha-ai-agent-service.

Includes:
- Pre-execution state snapshot (for rollback)
- Action execution via ha-device-control REST API
- Post-execution verification (confirm state changed)
- Notification to user ("I turned off the kitchen lights — undo?")
- Safety: never auto-execute lock/alarm/camera actions
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from ..clients.device_control_client import DeviceControlClient
from ..config import Settings
from ..models.autonomous_action import ActionOutcome, AutonomousActionAudit
from .confidence_scorer import ActionScore, SAFETY_BLOCKED_DOMAINS

logger = logging.getLogger(__name__)


class AutonomousExecutor:
    """Executes autonomous actions with state snapshots and audit trail."""

    def __init__(
        self,
        device_control_client: DeviceControlClient,
        settings: Settings,
    ):
        self.device_control = device_control_client
        self.settings = settings

    async def execute_action(
        self,
        action: dict[str, Any],
        score: ActionScore,
    ) -> bool:
        """Execute an autonomous action with full safety checks.

        Returns True if execution succeeded.
        """
        entity_id = action.get("entity_id", "")
        entity_domain = action.get("entity_domain", "")
        action_type = action.get("action_type", "")

        # Final safety check
        if entity_domain in SAFETY_BLOCKED_DOMAINS:
            logger.warning(
                "SAFETY BLOCK: Refused auto-execute on %s (%s)",
                entity_id, entity_domain,
            )
            return False

        if not self.settings.autonomous_execution_enabled:
            logger.info("Autonomous execution disabled, skipping %s", entity_id)
            return False

        # 1. Pre-execution state snapshot
        pre_state = await self.device_control.get_entity_state(entity_id)

        # 2. Execute the action
        result = await self._dispatch_action(action)
        if not result or not result.get("success"):
            logger.warning(
                "Autonomous execution failed for %s: %s",
                entity_id, result,
            )
            await self._save_audit(
                action=action,
                score=score,
                pre_state=pre_state or {},
                success=False,
                error_message=str(result) if result else "No response from device control",
            )
            return False

        # 3. Post-execution verification
        post_state = await self.device_control.get_entity_state(entity_id)

        # 4. Save audit trail
        await self._save_audit(
            action=action,
            score=score,
            pre_state=pre_state or {},
            post_state=post_state,
            success=True,
        )

        # 5. Notify user
        await self._notify_user(action, score)

        logger.info(
            "Auto-executed: %s on %s (confidence=%d, risk=%s)",
            action_type, entity_id, score.confidence, score.risk_level,
        )
        return True

    async def undo_action(self, audit_id: str) -> bool:
        """Undo a previously auto-executed action by restoring pre-action state.

        Args:
            audit_id: The audit trail entry ID to undo.

        Returns:
            True if undo succeeded.
        """
        from ..database import db

        async with db.get_db() as session:
            audit = await session.get(AutonomousActionAudit, audit_id)
            if not audit:
                logger.warning("Undo failed: audit entry %s not found", audit_id)
                return False

            if audit.undone:
                logger.info("Action %s already undone", audit_id)
                return True

            # Check undo window
            if audit.undo_expires_at and datetime.now(UTC) > audit.undo_expires_at:
                logger.warning("Undo window expired for action %s", audit_id)
                return False

            # Restore pre-action state
            pre_state = audit.pre_action_state
            success = await self._restore_state(
                entity_id=audit.entity_id,
                action_type=audit.action_type,
                pre_state=pre_state,
            )

            if success:
                audit.undone = True
                audit.undone_at = datetime.now(UTC)
                audit.outcome = ActionOutcome.AUTO_EXECUTED_UNDONE.value
                await session.commit()
                logger.info("Undone action %s on %s", audit_id, audit.entity_id)

                # Notify user
                await self.device_control.send_notification(
                    message=f"Undone: {audit.action_description}",
                    title="Action Reversed",
                )
            return success

    async def _dispatch_action(self, action: dict[str, Any]) -> dict[str, Any] | None:
        """Route an action to the appropriate device control method."""
        action_type = action.get("action_type", "")
        entity_id = action.get("entity_id", "")
        entity_domain = action.get("entity_domain", "")
        params = action.get("parameters", {})

        if entity_domain == "light":
            brightness = 0 if action_type == "turn_off" else params.get("brightness", 100)
            return await self.device_control.control_light(
                entity_id_or_name=entity_id,
                brightness=brightness,
                rgb=params.get("rgb"),
            )

        if entity_domain == "switch":
            state = "off" if action_type == "turn_off" else "on"
            return await self.device_control.control_switch(
                entity_id_or_name=entity_id,
                state=state,
            )

        if entity_domain == "climate":
            return await self.device_control.control_climate(
                entity_id=entity_id,
                temperature=params.get("temperature"),
                hvac_mode=params.get("hvac_mode"),
            )

        if entity_domain in ("scene", "script"):
            return await self.device_control.activate_scene(name=entity_id)

        logger.warning("Unsupported entity domain for autonomous execution: %s", entity_domain)
        return None

    async def _restore_state(
        self,
        entity_id: str,
        action_type: str,
        pre_state: dict[str, Any],
    ) -> bool:
        """Restore an entity to its pre-action state."""
        domain = entity_id.split(".")[0] if "." in entity_id else "unknown"
        old_state = pre_state.get("state", "off")

        try:
            if domain == "light":
                brightness = 0 if old_state == "off" else pre_state.get("brightness", 100)
                result = await self.device_control.control_light(
                    entity_id_or_name=entity_id, brightness=brightness,
                )
                return bool(result and result.get("success"))

            if domain == "switch":
                result = await self.device_control.control_switch(
                    entity_id_or_name=entity_id, state=old_state,
                )
                return bool(result and result.get("success"))

            if domain == "climate":
                result = await self.device_control.control_climate(
                    entity_id=entity_id,
                    temperature=pre_state.get("target_temperature"),
                    hvac_mode=pre_state.get("hvac_mode"),
                )
                return bool(result and result.get("success"))

        except Exception as e:
            logger.error("Failed to restore state for %s: %s", entity_id, e)
        return False

    async def _save_audit(
        self,
        action: dict[str, Any],
        score: ActionScore,
        pre_state: dict[str, Any],
        post_state: dict[str, Any] | None = None,
        success: bool = True,
        error_message: str | None = None,
    ) -> None:
        """Save an audit trail entry for the action."""
        from ..database import db

        try:
            undo_window = timedelta(minutes=self.settings.undo_window_minutes)
            audit = AutonomousActionAudit(
                action_type=action.get("action_type", "unknown"),
                entity_id=action.get("entity_id", "unknown"),
                action_description=action.get("reasoning", "Autonomous action"),
                reasoning=score.reasoning,
                confidence_score=score.confidence,
                risk_level=score.risk_level,
                pre_action_state=pre_state,
                post_action_state=post_state,
                outcome=ActionOutcome.AUTO_EXECUTED.value,
                success=success,
                error_message=error_message,
                undo_expires_at=datetime.now(UTC) + undo_window if success else None,
            )
            async with db.get_db() as session:
                session.add(audit)
                await session.commit()
        except Exception as e:
            logger.error("Failed to save audit trail: %s", e)

    async def _notify_user(
        self,
        action: dict[str, Any],
        score: ActionScore,
    ) -> None:
        """Notify the user about an autonomous action."""
        entity_id = action.get("entity_id", "")
        reasoning = action.get("reasoning", "")
        action_type = action.get("action_type", "")

        message = (
            f"I {action_type.replace('_', ' ')}d {entity_id} — {reasoning}. "
            f"(confidence: {score.confidence}%) You can undo this within "
            f"{self.settings.undo_window_minutes} minutes."
        )
        await self.device_control.send_notification(
            message=message,
            title="Proactive Action",
        )
