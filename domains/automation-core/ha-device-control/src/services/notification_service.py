"""HA notification service.

Sends notifications via Home Assistant's notify service,
ported from Sapphire's homeassistant.py:804-854.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .ha_rest_client import HARestClient

from .light_controller import ControlResult

logger = logging.getLogger(__name__)


class NotificationService:
    """Sends notifications through HA's notify service platform."""

    def __init__(
        self,
        ha_client: HARestClient,
        default_service: str = "",
    ) -> None:
        self._ha = ha_client
        self._default_service = default_service

    async def send(
        self,
        message: str,
        title: str | None = None,
        target: str | None = None,
    ) -> ControlResult:
        """Send a notification via HA's notify service.

        Args:
            message: Notification body text.
            title: Optional notification title.
            target: Optional notify service name override.
                    Defaults to the configured default service.

        Returns:
            ControlResult with outcome.
        """
        service_name = target or self._default_service
        if not service_name:
            return ControlResult(
                success=False,
                affected=[],
                message=(
                    "No notification service configured. "
                    "Set DEFAULT_NOTIFY_SERVICE or provide a target. "
                    "Find available services in HA Developer Tools > Services "
                    "under 'notify.*'."
                ),
            )

        # Strip 'notify.' prefix if user included it
        service_name = service_name.removeprefix("notify.")

        data: dict[str, str] = {"message": message}
        if title:
            data["title"] = title

        try:
            await self._ha.call_service("notify", service_name, data)
            logger.info("Notification sent via notify.%s", service_name)
            return ControlResult(
                success=True,
                affected=[f"notify.{service_name}"],
                message=f"Notification sent via notify.{service_name}",
            )
        except Exception as exc:
            error_msg = str(exc)
            # Provide helpful guidance for 404 errors
            if "404" in error_msg or "not found" in error_msg.lower():
                return ControlResult(
                    success=False,
                    affected=[],
                    message=(
                        f"Notify service 'notify.{service_name}' not found. "
                        "Check HA Developer Tools > Services for available "
                        "notify services (e.g. notify.mobile_app_yourphone)."
                    ),
                )
            logger.exception("Failed to send notification via notify.%s", service_name)
            return ControlResult(
                success=False,
                affected=[],
                message=f"Failed to send notification: {error_msg}",
            )
