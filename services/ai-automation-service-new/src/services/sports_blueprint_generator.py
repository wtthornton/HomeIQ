"""
Parameterized Sports-Lights Blueprint Generator

Epic: Platform-Wide Pattern Rollout, Story 10
Generates 5 automations from a single parameterized sports-lights blueprint:
kickoff, team A score, team B score, game over, and reset helpers.
"""

import logging
import sys
from pathlib import Path
from typing import Any

import yaml

try:
    _project_root = str(Path(__file__).resolve().parents[4])
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)
except IndexError:
    pass  # Docker: PYTHONPATH already includes /app

logger = logging.getLogger(__name__)


def generate_sports_automations(
    team_sensor: str,
    wled_entities: list[str],
    hue_entities: list[str],
    team_a_color: list[int],
    team_b_color: list[int],
    helper_prefix: str = "sports",
) -> list[dict[str, Any]]:
    """
    Generate 5 sports-lights automations from parameters.

    Args:
        team_sensor: Team Tracker sensor entity_id (e.g., sensor.nfl_team_tracker)
        wled_entities: List of WLED light entity_ids
        hue_entities: List of Hue light entity_ids
        team_a_color: RGB color for team A [R, G, B]
        team_b_color: RGB color for team B [R, G, B]
        helper_prefix: Prefix for helper entities (default: "sports")

    Returns:
        List of 5 automation dictionaries ready for deployment
    """
    all_lights = wled_entities + hue_entities
    prefix = helper_prefix

    # 1. Kickoff / Game Start
    kickoff = {
        "alias": f"{prefix}_game_kickoff",
        "description": "Flash team colors when game starts (state changes to IN)",
        "trigger": [
            {
                "platform": "state",
                "entity_id": team_sensor,
                "to": "IN",
            }
        ],
        "action": [
            {
                "service": "input_boolean.turn_on",
                "target": {"entity_id": f"input_boolean.{prefix}_game_active"},
            },
            {
                "service": "light.turn_on",
                "target": {"entity_id": all_lights},
                "data": {
                    "rgb_color": team_a_color,
                    "brightness": 255,
                },
            },
        ],
        "mode": "single",
    }

    # 2. Team A Score
    team_a_score = {
        "alias": f"{prefix}_team_a_score",
        "description": "Celebrate when your team scores",
        "trigger": [
            {
                "platform": "state",
                "entity_id": team_sensor,
                "attribute": "team_score",
            }
        ],
        "condition": [
            {
                "condition": "template",
                "value_template": (
                    "{{ trigger.to_state.attributes.team_score | int > "
                    "trigger.from_state.attributes.team_score | int }}"
                ),
            },
            {
                "condition": "state",
                "entity_id": f"input_boolean.{prefix}_game_active",
                "state": "on",
            },
        ],
        "action": [
            {
                "service": "light.turn_on",
                "target": {"entity_id": wled_entities},
                "data": {
                    "effect": "Color Wipe",
                    "rgb_color": team_a_color,
                    "brightness": 255,
                },
            },
            {
                "service": "light.turn_on",
                "target": {"entity_id": hue_entities},
                "data": {
                    "rgb_color": team_a_color,
                    "brightness": 255,
                    "flash": "long",
                },
            },
            {"delay": {"seconds": 30}},
            {
                "service": "light.turn_on",
                "target": {"entity_id": all_lights},
                "data": {
                    "rgb_color": team_a_color,
                    "brightness": 150,
                },
            },
        ],
        "mode": "single",
    }

    # 3. Team B Score (opponent)
    team_b_score = {
        "alias": f"{prefix}_team_b_score",
        "description": "Dim lights when opponent scores",
        "trigger": [
            {
                "platform": "state",
                "entity_id": team_sensor,
                "attribute": "opponent_score",
            }
        ],
        "condition": [
            {
                "condition": "template",
                "value_template": (
                    "{{ trigger.to_state.attributes.opponent_score | int > "
                    "trigger.from_state.attributes.opponent_score | int }}"
                ),
            },
            {
                "condition": "state",
                "entity_id": f"input_boolean.{prefix}_game_active",
                "state": "on",
            },
        ],
        "action": [
            {
                "service": "light.turn_on",
                "target": {"entity_id": all_lights},
                "data": {
                    "rgb_color": team_b_color,
                    "brightness": 50,
                },
            },
            {"delay": {"seconds": 10}},
            {
                "service": "light.turn_on",
                "target": {"entity_id": all_lights},
                "data": {
                    "rgb_color": team_a_color,
                    "brightness": 150,
                },
            },
        ],
        "mode": "single",
    }

    # 4. Game Over
    game_over = {
        "alias": f"{prefix}_game_over",
        "description": "Game over — restore normal lighting",
        "trigger": [
            {
                "platform": "state",
                "entity_id": team_sensor,
                "to": "POST",
            }
        ],
        "condition": [
            {
                "condition": "state",
                "entity_id": f"input_boolean.{prefix}_game_active",
                "state": "on",
            },
        ],
        "action": [
            {
                "service": "light.turn_on",
                "target": {"entity_id": all_lights},
                "data": {
                    "brightness": 200,
                    "color_temp": 350,
                },
            },
            {
                "service": "input_boolean.turn_off",
                "target": {"entity_id": f"input_boolean.{prefix}_game_active"},
            },
        ],
        "mode": "single",
    }

    # 5. Reset Helpers
    reset_helpers = {
        "alias": f"{prefix}_reset_helpers",
        "description": "Reset game helpers at midnight",
        "trigger": [
            {
                "platform": "time",
                "at": "00:00:00",
            }
        ],
        "action": [
            {
                "service": "input_boolean.turn_off",
                "target": {"entity_id": f"input_boolean.{prefix}_game_active"},
            },
        ],
        "mode": "single",
    }

    return [kickoff, team_a_score, team_b_score, game_over, reset_helpers]


def render_sports_blueprint_yaml(
    team_sensor: str,
    wled_entities: list[str],
    hue_entities: list[str],
    team_a_color: list[int],
    team_b_color: list[int],
    helper_prefix: str = "sports",
) -> str:
    """Generate sports automations and return as YAML string."""
    automations = generate_sports_automations(
        team_sensor=team_sensor,
        wled_entities=wled_entities,
        hue_entities=hue_entities,
        team_a_color=team_a_color,
        team_b_color=team_b_color,
        helper_prefix=helper_prefix,
    )
    return yaml.dump(automations, default_flow_style=False, sort_keys=False)
