"""
Action Parser

Parses automation YAML to extract actions for execution.
Supports 2025 Home Assistant YAML format.
"""

import logging
from typing import Any

import yaml

from .action_exceptions import ActionParseError

logger = logging.getLogger(__name__)


class ActionParser:
    """
    Parser for extracting actions from automation YAML.

    Supports 2025 Home Assistant format:
    - actions: (plural) with action: field
    - Nested structures: sequence:, parallel:, repeat:, choose:
    - Delay parsing: delay: '00:00:02' or delay: {seconds: 2}
    """

    @staticmethod
    def parse_actions_from_yaml(yaml_str: str) -> list[dict[str, Any]]:
        """
        Parse actions from YAML string.

        Args:
            yaml_str: Automation YAML string

        Returns:
            List of parsed action dictionaries

        Raises:
            ActionParseError: If parsing fails
        """
        try:
            automation_dict = yaml.safe_load(yaml_str)
            if not isinstance(automation_dict, dict):
                msg = "YAML must be a dictionary"
                raise ActionParseError(msg)

            return ActionParser.parse_actions_from_dict(automation_dict)
        except yaml.YAMLError as e:
            msg = f"YAML parsing error: {e}"
            raise ActionParseError(msg)
        except Exception as e:
            msg = f"Error parsing actions: {e}"
            raise ActionParseError(msg)

    @staticmethod
    def parse_actions_from_dict(automation_dict: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Parse actions from automation dictionary.

        Args:
            automation_dict: Automation dictionary (parsed from YAML)

        Returns:
            List of parsed action dictionaries
        """
        actions = automation_dict.get("actions", [])
        if not actions:
            logger.warning("No 'actions' key found in automation")
            return []

        parsed_actions = []
        for action_item in actions:
            try:
                parsed = ActionParser._extract_action(action_item)
                if parsed:
                    parsed_actions.append(parsed)
            except Exception as e:
                logger.warning(f"Failed to parse action item: {e}")
                continue

        return parsed_actions

    @staticmethod
    def _extract_action(action_item: dict[str, Any]) -> dict[str, Any] | None:
        """
        Extract action from action item.

        Handles:
        - Service calls: action: domain.service
        - Delays: delay: '00:00:02' or delay: {seconds: 2}
        - Sequences: sequence: [...]
        - Parallel: parallel: [...]
        - Repeat: repeat: {...}
        - Choose: choose: [...]

        Args:
            action_item: Action item dictionary

        Returns:
            Parsed action dictionary or None if not a valid action
        """
        # Handle delay
        if "delay" in action_item:
            delay_value = action_item["delay"]
            delay_seconds = ActionParser._parse_delay_value(delay_value)
            return {"delay": delay_seconds, "type": "delay"}

        # Handle service call (2025 format: action: domain.service)
        if "action" in action_item:
            action_str = action_item["action"]
            if not isinstance(action_str, str) or "." not in action_str:
                msg = f"Invalid action format: {action_str}"
                raise ActionParseError(msg)

            domain, service = action_str.split(".", 1)

            parsed_action = {
                "type": "service_call",
                "domain": domain,
                "service": service,
                "action": action_str,
            }

            # Extract target (2025 format: target.entity_id)
            if "target" in action_item:
                target = action_item["target"]
                if isinstance(target, dict):
                    parsed_action["target"] = target
                else:
                    # Legacy format: entity_id directly
                    parsed_action["target"] = {"entity_id": target}

            # Extract service data
            if "data" in action_item:
                parsed_action["data"] = action_item["data"]

            return parsed_action

        # Handle sequence
        if "sequence" in action_item:
            sequence_actions = []
            for seq_item in action_item["sequence"]:
                parsed = ActionParser._extract_action(seq_item)
                if parsed:
                    sequence_actions.append(parsed)
            return {"type": "sequence", "actions": sequence_actions}

        # Handle parallel
        if "parallel" in action_item:
            parallel_actions = []
            for par_item in action_item["parallel"]:
                parsed = ActionParser._extract_action(par_item)
                if parsed:
                    parallel_actions.append(parsed)
            return {"type": "parallel", "actions": parallel_actions}

        # Handle repeat
        if "repeat" in action_item:
            repeat_config = action_item["repeat"]
            repeat_actions = []
            for rep_item in repeat_config.get("sequence", []):
                parsed = ActionParser._extract_action(rep_item)
                if parsed:
                    repeat_actions.append(parsed)
            return {
                "type": "repeat",
                "count": repeat_config.get("count", 1),
                "actions": repeat_actions,
            }

        # Handle choose
        if "choose" in action_item:
            choose_actions = []
            for choice in action_item["choose"]:
                choice_actions = []
                for ch_item in choice.get("sequence", []):
                    parsed = ActionParser._extract_action(ch_item)
                    if parsed:
                        choice_actions.append(parsed)
                choose_actions.append({
                    "conditions": choice.get("conditions", []),
                    "sequence": choice_actions,
                })
            return {"type": "choose", "choices": choose_actions}

        # Unknown action type
        logger.warning(f"Unknown action type in item: {list(action_item.keys())}")
        return None

    @staticmethod
    def _parse_delay_value(delay: str | dict | float) -> float:
        """
        Parse delay value to seconds.

        Supports:
        - String: '00:00:02' or '00:02' or '2'
        - Dict: {seconds: 2} or {minutes: 1, seconds: 30}
        - Number: 2 (treated as seconds)

        Args:
            delay: Delay value in various formats

        Returns:
            Delay in seconds (float)
        """
        if isinstance(delay, (int, float)):
            return float(delay)

        if isinstance(delay, dict):
            total_seconds = 0.0
            if "seconds" in delay:
                total_seconds += float(delay["seconds"])
            if "minutes" in delay:
                total_seconds += float(delay["minutes"]) * 60
            if "hours" in delay:
                total_seconds += float(delay["hours"]) * 3600
            return total_seconds

        if isinstance(delay, str):
            # Parse time string: 'HH:MM:SS' or 'MM:SS' or 'SS'
            parts = delay.split(":")
            if len(parts) == 3:
                # HH:MM:SS
                hours, minutes, seconds = map(float, parts)
                return hours * 3600 + minutes * 60 + seconds
            if len(parts) == 2:
                # MM:SS
                minutes, seconds = map(float, parts)
                return minutes * 60 + seconds
            # SS
            return float(delay)

        msg = f"Invalid delay format: {delay}"
        raise ActionParseError(msg)

