"""
Agent Evaluation Framework — Synthetic Session Generator

Generates realistic SessionTrace objects from an AgentEvalConfig for
baseline evaluation runs when real production sessions aren't available.

Each generated session exercises the agent's tools, paths, and parameter
rules with a mix of success/failure scenarios.
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone

from .config import AgentEvalConfig, ParamDef, PathRule, ToolDef
from .models import AgentResponse, SessionTrace, ToolCall, UserMessage


# ---------------------------------------------------------------------------
# Scenario templates
# ---------------------------------------------------------------------------

_SCENARIO_NAMES = [
    "happy_path",
    "happy_path_alt",
    "partial_success",
    "wrong_tool_order",
    "missing_params",
    "error_session",
]

# Generic user prompts per scenario type
_USER_PROMPTS = {
    "happy_path": "Please complete the standard workflow",
    "happy_path_alt": "Run the full process end to end",
    "partial_success": "Do this quickly, skip optional steps",
    "wrong_tool_order": "Just execute it now, skip the preview",
    "missing_params": "Create something for me",
    "error_session": "Handle this automation request",
}

# Agent-specific user prompts (keyed by agent_name)
_AGENT_PROMPTS: dict[str, dict[str, str]] = {
    "ha-ai-agent": {
        "happy_path": "Create an automation to turn on lights at sunset",
        "happy_path_alt": "Set up a motion-activated hallway light",
        "partial_success": "Make a quick light timer automation",
        "wrong_tool_order": "Just deploy the automation immediately",
        "missing_params": "Create an automation",
        "error_session": "Make an automation for the kitchen",
    },
    "proactive-agent": {
        "happy_path": "Generate weather-based suggestions for today",
        "happy_path_alt": "Create an energy optimization suggestion",
        "partial_success": "Quick suggestion for sports event",
        "wrong_tool_order": "Send a suggestion to HA agent now",
        "missing_params": "Generate suggestions",
        "error_session": "Create suggestions for upcoming events",
    },
    "ai-automation-service": {
        "happy_path": "Deploy automation: turn on lights at sunset",
        "happy_path_alt": "Create and deploy a morning routine automation",
        "partial_success": "Quick deploy for temperature control",
        "wrong_tool_order": "Deploy without validating first",
        "missing_params": "Deploy something",
        "error_session": "Deploy the automation for the living room",
    },
    "ai-core-service": {
        "happy_path": "Analyze patterns in device usage data",
        "happy_path_alt": "Run full analysis: embed, cluster, detect anomalies",
        "partial_success": "Quick clustering of recent data",
        "wrong_tool_order": "Cluster data without embedding first",
        "missing_params": "Analyze the data",
        "error_session": "Generate suggestions from device patterns",
    },
}

# Agent-specific response templates
_AGENT_RESPONSES: dict[str, dict[str, str]] = {
    "ha-ai-agent": {
        "happy_path": "Here's a preview of your sunset light automation. The automation will trigger at sunset and turn on light.living_room. Would you like me to create it?",
        "happy_path_alt": "I've generated a preview for your motion-activated hallway light automation. It uses binary_sensor.hallway_motion as the trigger.",
        "partial_success": "I've created a basic timer automation. Note: some optional parameters were set to defaults.",
        "wrong_tool_order": "I've created the automation directly. Note: the preview step was skipped.",
        "missing_params": "I'll need more details, but here's a basic automation template.",
        "error_session": "I encountered an error while processing your request. The kitchen entity could not be resolved.",
    },
    "proactive-agent": {
        "happy_path": "Based on today's weather (32C, sunny), I suggest pre-cooling your home before peak heat at 2pm. Quality score: 0.88.",
        "happy_path_alt": "Current energy prices are low. I suggest running your dishwasher and laundry now for optimal savings.",
        "partial_success": "Found a sports event tonight. Generated a basic lighting suggestion.",
        "wrong_tool_order": "Sent suggestion directly to HA Agent without full context analysis.",
        "missing_params": "Generated a generic suggestion without specific context.",
        "error_session": "Error fetching context data from weather API. Unable to generate contextual suggestions.",
    },
    "ai-automation-service": {
        "happy_path": "Plan created, validated, compiled, and deployed successfully. Automation automation.sunset_lights is now active and verified.",
        "happy_path_alt": "Morning routine automation deployed. All 3 actions verified: lights, thermostat, and coffee maker.",
        "partial_success": "Automation deployed but verification returned a warning about entity availability.",
        "wrong_tool_order": "Deployed without validation. Warning: this bypasses safety checks.",
        "missing_params": "Created a plan but missing required template parameters.",
        "error_session": "Deployment failed: compiled YAML contained an invalid entity reference.",
    },
    "ai-core-service": {
        "happy_path": "Analysis complete: embedded 50 items, found 3 clusters with distinct usage patterns.",
        "happy_path_alt": "Full pipeline complete: 50 embeddings generated, 4 clusters identified, 2 anomalies detected.",
        "partial_success": "Clustering completed with default parameters. Some embeddings had low confidence.",
        "wrong_tool_order": "Attempted clustering without embeddings. Using raw data fallback.",
        "missing_params": "Analysis started but context data was incomplete.",
        "error_session": "ML service unavailable. Circuit breaker triggered after 3 retries.",
    },
}


class SyntheticSessionGenerator:
    """
    Generate synthetic SessionTrace objects from an AgentEvalConfig.

    Produces a deterministic mix of scenarios (happy path, partial success,
    wrong order, missing params, error) that exercise the agent's configured
    tools, paths, and parameter rules.

    Usage::

        config = ConfigLoader.load("configs/ha_ai_agent.yaml")
        generator = SyntheticSessionGenerator(config)
        sessions = generator.generate(count=5, seed=42)
    """

    def __init__(self, config: AgentEvalConfig):
        self.config = config

    def generate(self, count: int = 5, seed: int = 42) -> list[SessionTrace]:
        """Generate ``count`` synthetic sessions with deterministic randomness."""
        rng = random.Random(seed)
        sessions: list[SessionTrace] = []

        for i in range(count):
            scenario = _SCENARIO_NAMES[i % len(_SCENARIO_NAMES)]
            session = self._build_session(scenario, rng, i)
            sessions.append(session)

        return sessions

    def _build_session(
        self, scenario: str, rng: random.Random, index: int
    ) -> SessionTrace:
        """Build a single session for the given scenario."""
        agent = self.config.agent_name
        user_prompt = _AGENT_PROMPTS.get(agent, _USER_PROMPTS).get(
            scenario, _USER_PROMPTS.get(scenario, "Execute the task")
        )
        agent_response = _AGENT_RESPONSES.get(agent, {}).get(
            scenario, f"Task completed ({scenario})"
        )

        tool_calls = self._build_tool_calls(scenario, rng)
        metadata: dict = {}
        if scenario == "error_session":
            metadata["error"] = True
            metadata["error_message"] = "Service returned an unexpected error"

        return SessionTrace(
            session_id=str(uuid.UUID(int=rng.getrandbits(128), version=4)),
            agent_name=agent,
            timestamp=datetime.now(timezone.utc),
            model=self.config.model,
            temperature=0.7,
            user_messages=[UserMessage(content=user_prompt, turn_index=0)],
            agent_responses=[
                AgentResponse(content=agent_response, turn_index=1)
            ],
            tool_calls=tool_calls,
            metadata=metadata,
        )

    def _build_tool_calls(
        self, scenario: str, rng: random.Random
    ) -> list[ToolCall]:
        """Build tool calls appropriate for the scenario."""
        if scenario in ("happy_path", "happy_path_alt"):
            return self._happy_path_calls(rng, alt=(scenario == "happy_path_alt"))
        elif scenario == "partial_success":
            return self._partial_success_calls(rng)
        elif scenario == "wrong_tool_order":
            return self._wrong_order_calls(rng)
        elif scenario == "missing_params":
            return self._missing_params_calls(rng)
        elif scenario == "error_session":
            return self._error_session_calls(rng)
        return []

    def _happy_path_calls(
        self, rng: random.Random, alt: bool = False
    ) -> list[ToolCall]:
        """Generate tool calls following the correct path sequence."""
        if not self.config.paths:
            return self._all_tools_sequential(rng)

        # Use first path for happy_path, second (or first) for alt
        path_index = min(1, len(self.config.paths) - 1) if alt else 0
        path = self.config.paths[path_index]
        return self._calls_from_path(path, rng, all_params_valid=True)

    def _partial_success_calls(self, rng: random.Random) -> list[ToolCall]:
        """Correct tool sequence but some params have issues."""
        if not self.config.paths:
            return self._all_tools_sequential(rng, partial=True)

        path = self.config.paths[0]
        calls = self._calls_from_path(path, rng, all_params_valid=False)
        # Reduce params on some calls
        for call in calls:
            if rng.random() < 0.3 and call.parameters:
                # Remove one optional param
                optional_keys = [
                    k for k in call.parameters
                    if k not in self._required_params_for(call.tool_name)
                ]
                if optional_keys:
                    del call.parameters[rng.choice(optional_keys)]
        return calls

    def _wrong_order_calls(self, rng: random.Random) -> list[ToolCall]:
        """Tool calls in wrong order — violates path rules."""
        if not self.config.paths:
            tools = [t.name for t in self.config.tools]
            rng.shuffle(tools)
            return [
                self._make_tool_call(name, idx, rng)
                for idx, name in enumerate(tools[:3])
            ]

        path = self.config.paths[0]
        # Reverse the sequence
        reversed_seq = list(reversed(path.sequence))
        return [
            self._make_tool_call(name, idx, rng)
            for idx, name in enumerate(reversed_seq)
        ]

    def _missing_params_calls(self, rng: random.Random) -> list[ToolCall]:
        """Tool calls with missing required parameters."""
        if not self.config.paths:
            tool = self.config.tools[0] if self.config.tools else None
            if not tool:
                return []
            return [self._make_tool_call(tool.name, 0, rng, skip_required=True)]

        path = self.config.paths[0]
        calls = []
        for idx, tool_name in enumerate(path.sequence):
            call = self._make_tool_call(tool_name, idx, rng, skip_required=True)
            calls.append(call)
        return calls

    def _error_session_calls(self, rng: random.Random) -> list[ToolCall]:
        """Session where a tool call returns an error."""
        if not self.config.tools:
            return []

        tool = self.config.tools[0]
        return [
            ToolCall(
                tool_name=tool.name,
                parameters=self._generate_params(tool, rng),
                result={"error": True, "message": "Service unavailable"},
                sequence_index=0,
                turn_index=0,
                latency_ms=rng.uniform(500, 5000),
            )
        ]

    def _calls_from_path(
        self,
        path: PathRule,
        rng: random.Random,
        all_params_valid: bool = True,
    ) -> list[ToolCall]:
        """Generate tool calls following a PathRule sequence."""
        calls = []
        for idx, tool_name in enumerate(path.sequence):
            call = self._make_tool_call(
                tool_name, idx, rng, all_params_valid=all_params_valid
            )
            calls.append(call)
        return calls

    def _all_tools_sequential(
        self, rng: random.Random, partial: bool = False
    ) -> list[ToolCall]:
        """Use all tools in order (fallback when no paths defined)."""
        calls = []
        for idx, tool in enumerate(self.config.tools):
            call = self._make_tool_call(
                tool.name, idx, rng, all_params_valid=not partial
            )
            calls.append(call)
        return calls

    def _make_tool_call(
        self,
        tool_name: str,
        sequence_index: int,
        rng: random.Random,
        all_params_valid: bool = True,
        skip_required: bool = False,
    ) -> ToolCall:
        """Create a single ToolCall with realistic parameters."""
        tool = self.config.get_tool(tool_name)
        if tool is None:
            return ToolCall(
                tool_name=tool_name,
                parameters={},
                result={"status": "ok"},
                sequence_index=sequence_index,
                turn_index=0,
                latency_ms=rng.uniform(50, 500),
            )

        params = self._generate_params(
            tool, rng, skip_required=skip_required
        )
        result = self._generate_result(tool, rng, all_params_valid)

        return ToolCall(
            tool_name=tool_name,
            parameters=params,
            result=result,
            sequence_index=sequence_index,
            turn_index=0,
            latency_ms=rng.uniform(50, 500),
        )

    def _generate_params(
        self,
        tool: ToolDef,
        rng: random.Random,
        skip_required: bool = False,
    ) -> dict:
        """Generate parameter values from the tool's parameter definitions."""
        params = {}
        for param_def in tool.parameters:
            if skip_required and param_def.name in tool.required_params:
                if rng.random() < 0.5:
                    continue  # Skip ~50% of required params
            if not param_def.required and rng.random() < 0.3:
                continue  # Skip optional params 30% of the time

            params[param_def.name] = self._generate_param_value(param_def, rng)
        return params

    def _generate_param_value(
        self, param_def: ParamDef, rng: random.Random
    ) -> object:
        """Generate a realistic value for a parameter."""
        # Use valid_values if available
        if param_def.valid_values:
            return rng.choice(param_def.valid_values)

        # Generate by type
        ptype = param_def.type.lower()
        if ptype == "string":
            return self._string_value_for(param_def.name, rng)
        elif ptype == "integer":
            lo = int(param_def.min_value or 1)
            hi = int(param_def.max_value or 10)
            return rng.randint(lo, hi)
        elif ptype == "float":
            lo = param_def.min_value or 0.0
            hi = param_def.max_value or 1.0
            return round(rng.uniform(lo, hi), 2)
        elif ptype == "boolean":
            return rng.choice([True, False])
        elif ptype in ("list", "array"):
            return [self._string_value_for(param_def.name, rng)]
        elif ptype in ("object", "dict"):
            return {"key": "value"}
        return "sample_value"

    @staticmethod
    def _string_value_for(param_name: str, rng: random.Random) -> str:
        """Generate a context-appropriate string value based on param name."""
        name_map: dict[str, list[str]] = {
            "user_prompt": [
                "Turn on lights at sunset",
                "Create a morning routine",
                "Set up motion-activated lights",
            ],
            "user_text": [
                "Turn on lights at sunset",
                "Automate the thermostat for winter",
            ],
            "automation_yaml": [
                "alias: Sunset Lights\ndescription: Turn on lights at sunset\ninitial_state: true\nmode: single\ntrigger:\n  - platform: sun\n    event: sunset\naction:\n  - service: light.turn_on\n    target:\n      entity_id: light.living_room",
            ],
            "alias": ["Sunset Lights", "Morning Routine", "Motion Hallway"],
            "original_prompt": ["Turn on lights at sunset"],
            "prompt": ["Pre-cool your home before the afternoon heat wave"],
            "suggestion_id": ["sug_001", "sug_002", "sug_003"],
            "plan_id": ["plan_001", "plan_002"],
            "template_id": ["tmpl_light_on", "tmpl_thermostat"],
            "template_version": ["1.0", "2.0"],
            "compiled_id": ["comp_001", "comp_002"],
            "approved_by": ["user", "admin"],
            "deployment_id": ["dep_001", "dep_002"],
            "automation_id": ["automation.sunset_lights", "automation.morning_routine"],
            "yaml_content": [
                "alias: Test\ndescription: Test automation\ntrigger:\n  - platform: state\naction:\n  - service: light.turn_on"
            ],
            "pattern_description": [
                "Lights turned on every day at 6pm",
                "Thermostat adjusted when nobody home",
            ],
            "conversation_id": ["conv_001", "conv_002"],
        }
        candidates = name_map.get(param_name, [f"sample_{param_name}_value"])
        return rng.choice(candidates)

    def _generate_result(
        self, tool: ToolDef, rng: random.Random, success: bool = True
    ) -> dict:
        """Generate a realistic tool result."""
        if not success and rng.random() < 0.3:
            return {"error": True, "message": "Validation failed"}

        # Tool-specific results
        result_map: dict[str, dict] = {
            "preview_automation_from_prompt": {
                "preview_id": f"prev_{rng.randint(100, 999)}",
                "valid": True,
                "warnings": [],
                "affected_entities": ["light.living_room"],
            },
            "create_automation_from_prompt": {
                "automation_id": f"automation.auto_{rng.randint(100, 999)}",
                "created": True,
            },
            "suggest_automation_enhancements": {
                "suggestions": [
                    {"title": "Add time condition", "level": "conservative"},
                    {"title": "Add notification", "level": "balanced"},
                ],
            },
            "fetch_context": {
                "weather": {"temp": rng.randint(15, 40), "condition": "sunny"},
                "sports": {"events": []},
                "energy": {"carbon_intensity": rng.randint(50, 300)},
            },
            "analyze_context": {
                "insights": ["high_temperature", "low_carbon_window"],
                "opportunities": 2,
            },
            "generate_prompt": {
                "prompt": "Pre-cool your home before the afternoon heat",
                "generation_method": "ai",
            },
            "create_suggestion": {
                "suggestion_id": f"sug_{rng.randint(100, 999)}",
                "quality_score": round(rng.uniform(0.6, 0.95), 2),
                "status": "pending",
            },
            "send_to_ha_agent": {
                "sent": True,
                "ha_agent_response": "Received",
            },
            "create_plan": {
                "plan_id": f"plan_{rng.randint(100, 999)}",
                "template_id": "tmpl_light_on",
                "parameters": {"entity": "light.living_room"},
            },
            "validate_plan": {"valid": True, "errors": []},
            "compile_yaml": {
                "compiled_id": f"comp_{rng.randint(100, 999)}",
                "yaml": "alias: test\ntrigger:\n  - platform: sun",
            },
            "deploy_automation": {
                "deployment_id": f"dep_{rng.randint(100, 999)}",
                "status": "deployed",
            },
            "verify_deployment": {"success": True, "state": "on"},
            "rollback_automation": {"rolled_back": True, "previous_version": 1},
            "validate_yaml": {"valid": True, "errors": [], "warnings": []},
            "generate_embeddings": {
                "embeddings": [[round(rng.uniform(-1, 1), 3) for _ in range(4)]],
                "count": 1,
            },
            "classify_pattern": {
                "category": "usage_pattern",
                "priority": "medium",
                "confidence": round(rng.uniform(0.7, 0.99), 2),
            },
            "cluster_data": {
                "labels": [0, 1, 0, 1, 2],
                "n_clusters": 3,
            },
            "detect_anomalies": {
                "anomaly_labels": [1, -1, 1, 1, -1],
                "anomaly_count": 2,
            },
            "generate_suggestions": {
                "suggestions": [
                    "Optimize lighting schedule based on occupancy patterns",
                    "Reduce HVAC usage during low-occupancy hours",
                ],
            },
        }

        return result_map.get(tool.name, {"status": "ok", "data": {}})

    def _required_params_for(self, tool_name: str) -> list[str]:
        """Get required params for a tool."""
        tool = self.config.get_tool(tool_name)
        return tool.required_params if tool else []
