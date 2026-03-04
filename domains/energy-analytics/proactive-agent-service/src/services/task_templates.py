"""Built-in task templates for common scheduled automations.

Epic 27: Scheduled AI Tasks (Continuity)
Story 27.3: Built-in Task Templates
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TaskTemplate:
    """Immutable descriptor for a pre-built scheduled task."""

    id: str
    name: str
    cron_expression: str
    prompt: str
    notification_preference: str  # always / on_alert / never
    cooldown_minutes: int
    max_execution_seconds: int
    description: str


BUILT_IN_TEMPLATES: list[TaskTemplate] = [
    TaskTemplate(
        id="morning_briefing",
        name="Morning Briefing",
        cron_expression="0 7 * * *",
        prompt=(
            "Give me a morning briefing. Summarize any notable events from "
            "overnight (door/window opens, motion, alarms). Include the "
            "current weather forecast, today's energy usage so far compared "
            "to the weekly average, and any upcoming calendar events. "
            "Keep it concise — bullet points are fine."
        ),
        notification_preference="always",
        cooldown_minutes=60,
        max_execution_seconds=120,
        description="Daily 7 AM summary of overnight events, energy, and weather",
    ),
    TaskTemplate(
        id="security_check",
        name="Security Check",
        cron_expression="0 23 * * *",
        prompt=(
            "Perform a nightly security check. Verify that all exterior "
            "doors and windows are closed and locked. Check the garage door "
            "status. List any lights that are still on in unoccupied rooms. "
            "If anything is open or unusual, flag it as an alert."
        ),
        notification_preference="on_alert",
        cooldown_minutes=60,
        max_execution_seconds=90,
        description="Nightly 11 PM check of doors, windows, garage, and lights",
    ),
    TaskTemplate(
        id="energy_report",
        name="Weekly Energy Report",
        cron_expression="0 18 * * 5",
        prompt=(
            "Generate a weekly energy report. Summarize total energy "
            "consumption for the past 7 days compared to the previous week. "
            "Identify the top 3 energy-consuming devices or circuits. "
            "Highlight any unusual spikes or trends. Suggest one actionable "
            "tip to reduce energy usage next week."
        ),
        notification_preference="always",
        cooldown_minutes=1440,
        max_execution_seconds=120,
        description="Friday 6 PM weekly energy summary with trends and tips",
    ),
    TaskTemplate(
        id="device_health",
        name="Device Health Check",
        cron_expression="0 9 * * 1",
        prompt=(
            "Run a device health check. List any smart home devices that "
            "are currently offline or unavailable. Check for devices with "
            "low battery levels (below 20%). Identify any devices that "
            "have not reported data in the last 24 hours. Summarize the "
            "overall health of the smart home system."
        ),
        notification_preference="on_alert",
        cooldown_minutes=1440,
        max_execution_seconds=90,
        description="Monday 9 AM weekly check for offline or low-battery devices",
    ),
]

TEMPLATE_MAP: dict[str, TaskTemplate] = {t.id: t for t in BUILT_IN_TEMPLATES}


def get_template(template_id: str) -> TaskTemplate | None:
    """Return a template by its id, or None if not found."""
    return TEMPLATE_MAP.get(template_id)


def list_templates() -> list[TaskTemplate]:
    """Return all built-in templates."""
    return list(BUILT_IN_TEMPLATES)
