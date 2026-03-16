"""
Observe-Reason-Act Agent Loop (Epic 68, Story 68.1).

Replaces the passive cron → single-LLM-call → delegate pattern with
an autonomous agent loop that:
  1. Observes: aggregates current home state, weather, energy, time
  2. Reasons: LLM evaluates what proactive action would help (structured output)
  3. Acts: routes to autonomous execution or suggestion queue based on confidence/risk

The loop runs on a configurable interval (default: 15 minutes).
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime, time
from typing import Any

from ..clients.device_control_client import DeviceControlClient
from ..clients.ha_agent_client import HAAgentClient
from ..config import Settings
from ..models.autonomous_action import ActionOutcome
from .autonomous_executor import AutonomousExecutor
from .confidence_scorer import ActionScore, ConfidenceScorer, SAFETY_BLOCKED_DOMAINS
from .context_analysis_service import ContextAnalysisService
from .feedback_recorder import FeedbackRecorder
from .preference_service import PreferenceService

logger = logging.getLogger(__name__)

# Structured output prompt for the reasoning step
REASONING_PROMPT = """You are a proactive smart home assistant. Analyze the current home state and context, then propose actions that would help the user.

## Current Home State
{home_state}

## Weather Context
{weather_context}

## Time Context
{time_context}

## User Preference History
{preference_context}

## Instructions
Based on the above context, identify 0-3 proactive actions that would be helpful.
For each action, provide a JSON object with:
- action_type: the HA service to call (turn_off, turn_on, set_brightness, set_temperature, set_hvac_mode, activate_scene)
- entity_id: the HA entity ID to act on (e.g. light.kitchen, climate.living_room)
- entity_domain: the entity domain (light, switch, climate, scene)
- parameters: dict of parameters (brightness, temperature, etc.)
- confidence: your confidence this is helpful (0.0-1.0)
- reasoning: one sentence explaining why this action would help
- context_type: what triggered this suggestion (weather, energy, time_of_day, occupancy, comfort, safety)

Return ONLY a JSON array of action objects. If no actions are warranted, return an empty array [].
Do NOT suggest actions for locked doors, alarm systems, or cameras.

Response (JSON array only):"""


class ProactiveAgentLoop:
    """Observe-Reason-Act loop for autonomous proactive actions."""

    def __init__(
        self,
        settings: Settings,
        context_service: ContextAnalysisService | None = None,
        device_control_client: DeviceControlClient | None = None,
        agent_client: HAAgentClient | None = None,
        confidence_scorer: ConfidenceScorer | None = None,
        preference_service: PreferenceService | None = None,
        feedback_recorder: FeedbackRecorder | None = None,
        autonomous_executor: AutonomousExecutor | None = None,
    ):
        self.settings = settings
        self.context_service = context_service or ContextAnalysisService()
        self.device_control = device_control_client or DeviceControlClient(
            base_url=settings.ha_device_control_url,
            timeout=settings.ha_device_control_timeout,
        )
        self.agent_client = agent_client or HAAgentClient(
            base_url=settings.ha_ai_agent_url,
            timeout=settings.ha_ai_agent_timeout,
        )
        self.scorer = confidence_scorer or ConfidenceScorer(
            auto_execute_threshold=settings.auto_execute_confidence_threshold,
            suggest_threshold=settings.suggest_confidence_threshold,
            suppress_threshold=settings.suppress_confidence_threshold,
        )
        self.preference_service = preference_service or PreferenceService()
        self.feedback_recorder = feedback_recorder or FeedbackRecorder()
        self.executor = autonomous_executor or AutonomousExecutor(
            device_control_client=self.device_control,
            settings=settings,
        )

        # LLM client for reasoning step
        self._openai_client: Any = None
        self._task: asyncio.Task | None = None
        self._running = False

        # Metrics
        self.cycle_count = 0
        self.actions_proposed = 0
        self.actions_auto_executed = 0
        self.actions_suggested = 0
        self.actions_suppressed = 0

    async def start(self) -> None:
        """Start the agent loop as a background task."""
        if not self.settings.agent_loop_enabled:
            logger.info("Agent loop disabled in settings")
            return

        self._running = True
        self._init_openai_client()
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            "Proactive agent loop started (interval=%dm, auto_execute=%s)",
            self.settings.agent_loop_interval_minutes,
            self.settings.autonomous_execution_enabled,
        )

    async def stop(self) -> None:
        """Stop the agent loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Proactive agent loop stopped")

    async def _run_loop(self) -> None:
        """Main loop — observe, reason, act on interval."""
        interval = self.settings.agent_loop_interval_minutes * 60
        while self._running:
            try:
                await self.run_cycle()
            except Exception as e:
                logger.error("Agent loop cycle failed: %s", e, exc_info=True)
            await asyncio.sleep(interval)

    async def run_cycle(self) -> dict[str, Any]:
        """Execute one observe-reason-act cycle.

        Returns:
            Summary of cycle results.
        """
        self.cycle_count += 1
        cycle_start = datetime.now(UTC)
        logger.info("Agent loop cycle #%d starting", self.cycle_count)

        # --- OBSERVE ---
        observations = await self._observe()
        if not observations:
            logger.info("Cycle #%d: no observations available, skipping", self.cycle_count)
            return {"cycle": self.cycle_count, "status": "skipped", "reason": "no_observations"}

        # --- REASON ---
        proposed_actions = await self._reason(observations)
        if not proposed_actions:
            logger.info("Cycle #%d: no actions proposed", self.cycle_count)
            return {"cycle": self.cycle_count, "status": "no_actions", "proposed": 0}

        self.actions_proposed += len(proposed_actions)

        # --- ACT ---
        results = await self._act(proposed_actions, observations)

        duration = (datetime.now(UTC) - cycle_start).total_seconds()
        logger.info(
            "Cycle #%d complete in %.1fs: %d proposed, %d auto-executed, %d suggested, %d suppressed",
            self.cycle_count, duration,
            len(proposed_actions),
            results.get("auto_executed", 0),
            results.get("suggested", 0),
            results.get("suppressed", 0),
        )

        return {
            "cycle": self.cycle_count,
            "status": "completed",
            "duration_seconds": round(duration, 1),
            "proposed": len(proposed_actions),
            **results,
        }

    # --- OBSERVE STEP ---

    async def _observe(self) -> dict[str, Any] | None:
        """Aggregate current home state and context."""
        observations: dict[str, Any] = {}

        # House status from ha-device-control
        house_status = await self.device_control.get_house_status()
        if house_status:
            observations["home_state"] = house_status

        # Weather context
        try:
            weather = await self.context_service.get_weather_context()
            observations["weather"] = weather
        except Exception as e:
            logger.debug("Weather context unavailable: %s", e)

        # Time context
        now = datetime.now(UTC)
        observations["time"] = {
            "utc": now.isoformat(),
            "hour": now.hour,
            "day_of_week": now.strftime("%A"),
            "time_slot": self._get_time_slot(now.hour),
        }

        if not observations.get("home_state"):
            return None

        return observations

    # --- REASON STEP ---

    async def _reason(self, observations: dict[str, Any]) -> list[dict[str, Any]]:
        """Use LLM to reason about what proactive actions would help."""
        if not self._openai_client:
            return []

        # Get preference context for the LLM
        preference_context = await self.preference_service.get_preference_summary()

        # Build prompt
        prompt = REASONING_PROMPT.format(
            home_state=json.dumps(observations.get("home_state", {}), indent=2)[:3000],
            weather_context=json.dumps(observations.get("weather", {}), indent=2)[:500],
            time_context=json.dumps(observations.get("time", {}), indent=2),
            preference_context=preference_context or "No preference history available.",
        )

        try:
            from ..clients.breakers import openai_breaker

            async with openai_breaker:
                response = await self._openai_client.chat.completions.create(
                    model=self.settings.openai_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=1500,
                    response_format={"type": "json_object"},
                )

            content = response.choices[0].message.content
            if not content:
                return []

            # Parse JSON response
            parsed = json.loads(content)
            actions = parsed if isinstance(parsed, list) else parsed.get("actions", [])

            # Validate and filter actions
            valid_actions = []
            for action in actions[:3]:  # Max 3 per cycle
                if self._validate_proposed_action(action):
                    valid_actions.append(action)

            return valid_actions

        except Exception as e:
            logger.error("LLM reasoning failed: %s", e)
            return []

    # --- ACT STEP ---

    async def _act(
        self,
        proposed_actions: list[dict[str, Any]],
        observations: dict[str, Any],
    ) -> dict[str, int]:
        """Route each action to auto-execute, suggest, or suppress."""
        results = {"auto_executed": 0, "suggested": 0, "suppressed": 0}
        time_slot = observations.get("time", {}).get("time_slot", "afternoon")
        in_quiet = self._is_quiet_hours()

        for action in proposed_actions:
            entity_domain = action.get("entity_domain", "unknown")
            action_type = action.get("action_type", "unknown")

            # Get historical acceptance rate
            acceptance_rate = await self.preference_service.get_acceptance_rate(
                action_type=action_type,
                entity_domain=entity_domain,
                context_type=action.get("context_type", "unknown"),
                time_slot=time_slot,
            )

            # Score the action
            score = self.scorer.score_action(
                action_type=action_type,
                entity_domain=entity_domain,
                context_type=action.get("context_type", "unknown"),
                llm_confidence=action.get("confidence", 0.5),
                acceptance_rate=acceptance_rate,
                context_match_strength=0.6,
                time_slot=time_slot,
            )

            # Route
            route = self.scorer.evaluate_action_route(
                score=score,
                autonomous_enabled=self.settings.autonomous_execution_enabled,
                in_quiet_hours=in_quiet,
            )

            if route == "auto_execute":
                success = await self.executor.execute_action(action, score)
                if success:
                    self.actions_auto_executed += 1
                    results["auto_executed"] += 1
                    await self.feedback_recorder.record_outcome(
                        action=action,
                        outcome=ActionOutcome.AUTO_EXECUTED,
                        score=score,
                        time_slot=time_slot,
                    )
                else:
                    results["suppressed"] += 1

            elif route == "suggest":
                await self._surface_suggestion(action, score)
                self.actions_suggested += 1
                results["suggested"] += 1
                await self.feedback_recorder.record_outcome(
                    action=action,
                    outcome=ActionOutcome.SUGGESTED,
                    score=score,
                    time_slot=time_slot,
                )

            else:
                self.actions_suppressed += 1
                results["suppressed"] += 1
                await self.feedback_recorder.record_outcome(
                    action=action,
                    outcome=ActionOutcome.SUPPRESSED,
                    score=score,
                    time_slot=time_slot,
                )

        return results

    async def _surface_suggestion(
        self,
        action: dict[str, Any],
        score: ActionScore,
    ) -> None:
        """Surface an action as a suggestion via the existing pipeline."""
        from .suggestion_storage_service import SuggestionStorageService

        try:
            storage = SuggestionStorageService()
            await storage.store_suggestion(
                prompt=action.get("reasoning", "Proactive suggestion"),
                context_type=action.get("context_type", "proactive"),
                quality_score=score.confidence / 100.0,
                context_metadata={
                    "entity_id": action.get("entity_id"),
                    "action_type": action.get("action_type"),
                    "confidence": score.confidence,
                    "risk_level": score.risk_level,
                    "source": "agent_loop",
                },
                prompt_metadata={
                    "trigger": "observe_reason_act",
                    "reasoning": action.get("reasoning"),
                    "automation_hints": action.get("parameters", {}),
                },
            )
        except Exception as e:
            logger.error("Failed to store suggestion: %s", e)

    # --- HELPERS ---

    def _init_openai_client(self) -> None:
        """Initialize OpenAI client for reasoning step."""
        if not self.settings.openai_api_key:
            logger.warning("No OpenAI API key — agent loop reasoning disabled")
            return
        try:
            from openai import AsyncOpenAI

            self._openai_client = AsyncOpenAI(
                api_key=self.settings.openai_api_key,
                timeout=self.settings.openai_timeout,
            )
        except ImportError:
            logger.warning("openai package not installed — agent loop reasoning disabled")

    def _validate_proposed_action(self, action: dict[str, Any]) -> bool:
        """Validate a proposed action from LLM output."""
        required = ["action_type", "entity_id", "entity_domain", "reasoning"]
        if not all(k in action for k in required):
            return False
        # Block safety-critical domains
        if action.get("entity_domain") in SAFETY_BLOCKED_DOMAINS:
            logger.warning(
                "Blocked safety-critical action on %s", action.get("entity_id"),
            )
            return False
        return True

    def _is_quiet_hours(self) -> bool:
        """Check if current time is within quiet hours."""
        now = datetime.now(UTC)
        try:
            start = time.fromisoformat(self.settings.quiet_hours_start)
            end = time.fromisoformat(self.settings.quiet_hours_end)
        except ValueError:
            return False

        current = now.time()
        if start <= end:
            return start <= current <= end
        # Overnight (e.g. 23:00 - 06:00)
        return current >= start or current <= end

    @staticmethod
    def _get_time_slot(hour: int) -> str:
        """Map hour to time slot."""
        if 5 <= hour < 12:
            return "morning"
        if 12 <= hour < 17:
            return "afternoon"
        if 17 <= hour < 22:
            return "evening"
        return "night"

    def get_metrics(self) -> dict[str, Any]:
        """Return current agent loop metrics."""
        return {
            "cycle_count": self.cycle_count,
            "actions_proposed": self.actions_proposed,
            "actions_auto_executed": self.actions_auto_executed,
            "actions_suggested": self.actions_suggested,
            "actions_suppressed": self.actions_suppressed,
            "loop_running": self._running,
        }
