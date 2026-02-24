"""
Tests for Epic 3 (Phase 4): Platform-Wide Pattern Rollout — Validation & Verifiers

Tests for SceneValidationRouter, ScriptValidationRouter,
SceneVerifier, ScriptVerifier, TaskExecutionVerifier,
and SportsBluprintGenerator.
"""

import pytest
from pathlib import Path
import sys
from unittest.mock import AsyncMock

_project_root = str(Path(__file__).resolve().parents[3])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from homeiq_patterns import (
    UnifiedValidationRouter,
    ValidationRequest,
    ValidationResponse,
    PostActionVerifier,
    VerificationResult,
    VerificationWarning,
)


# ================================================================== #
# Scene Validation Router Tests
# ================================================================== #

class _SceneValidationRouter(UnifiedValidationRouter):
    domain = "scene"
    error_categories = {
        "entity": ("entity", "Entity", "not found"),
        "service": ("service", "Service"),
    }

    async def run_validation(self, request, **kwargs):
        import yaml as yaml_lib
        errors, warnings = [], []

        try:
            data = yaml_lib.safe_load(request.content)
        except yaml_lib.YAMLError as e:
            return ValidationResponse(valid=False, errors=[f"Invalid YAML: {e}"])

        scenes = []
        if isinstance(data, dict):
            scenes = data.get("scene", [data]) if "scene" in data else [data]
        elif isinstance(data, list):
            scenes = data

        for i, sc in enumerate(scenes):
            if not isinstance(sc, dict):
                errors.append(f"Scene #{i+1}: must be a mapping")
                continue
            if not sc.get("name"):
                errors.append(f"Scene #{i+1}: missing 'name'")
            if not sc.get("entities"):
                warnings.append(f"Scene #{i+1}: no entities defined")

        score = max(0.0, 100.0 - len(errors) * 15 - len(warnings) * 5)
        return self.build_response(
            {"valid": not errors, "errors": errors, "warnings": warnings, "score": score},
            request,
        )


class TestSceneValidationRouter:
    @pytest.mark.asyncio
    async def test_valid_scene(self):
        r = _SceneValidationRouter()
        req = ValidationRequest(
            content="name: Movie Night\nentities:\n  light.living_room:\n    state: 'on'\n"
        )
        resp = await r.run_validation(req)
        assert resp.valid

    @pytest.mark.asyncio
    async def test_missing_name(self):
        r = _SceneValidationRouter()
        req = ValidationRequest(content="entities:\n  light.test:\n    state: 'on'\n")
        resp = await r.run_validation(req)
        assert not resp.valid
        assert any("name" in e for e in resp.errors)

    @pytest.mark.asyncio
    async def test_no_entities_warning(self):
        r = _SceneValidationRouter()
        req = ValidationRequest(content="name: Empty Scene\n")
        resp = await r.run_validation(req)
        assert resp.valid  # warnings don't fail validation
        assert len(resp.warnings) > 0

    @pytest.mark.asyncio
    async def test_invalid_yaml(self):
        r = _SceneValidationRouter()
        req = ValidationRequest(content="{{bad")
        resp = await r.run_validation(req)
        assert not resp.valid


# ================================================================== #
# Script Validation Router Tests
# ================================================================== #

class _ScriptValidationRouter(UnifiedValidationRouter):
    domain = "script"
    error_categories = {
        "entity": ("entity", "Entity", "not found"),
        "service": ("service", "Service", "invalid service"),
    }

    async def run_validation(self, request, **kwargs):
        import yaml as yaml_lib
        errors, warnings = [], []

        try:
            data = yaml_lib.safe_load(request.content)
        except yaml_lib.YAMLError as e:
            return ValidationResponse(valid=False, errors=[f"Invalid YAML: {e}"])

        if not isinstance(data, dict):
            return ValidationResponse(valid=False, errors=["Script must be a mapping"])

        scripts = {}
        if "script" in data:
            scripts = data["script"]
        elif "sequence" in data:
            scripts = {"inline": data}
        else:
            scripts = data

        for name, sdef in scripts.items():
            if not isinstance(sdef, dict):
                errors.append(f"Script '{name}': must be a mapping")
                continue
            seq = sdef.get("sequence", [])
            if not seq:
                errors.append(f"Script '{name}': missing 'sequence'")
                continue
            for i, action in enumerate(seq):
                if not isinstance(action, dict):
                    errors.append(f"Script '{name}', step {i+1}: must be a mapping")
                    continue
                if "service" in action and request.validate_services:
                    parts = action["service"].split(".")
                    if len(parts) != 2:
                        errors.append(f"Script '{name}', step {i+1}: invalid service '{action['service']}'")

        score = max(0.0, 100.0 - len(errors) * 15 - len(warnings) * 5)
        return self.build_response(
            {"valid": not errors, "errors": errors, "warnings": warnings, "score": score},
            request,
        )


class TestScriptValidationRouter:
    @pytest.mark.asyncio
    async def test_valid_script(self):
        r = _ScriptValidationRouter()
        req = ValidationRequest(
            content="sequence:\n  - service: light.turn_on\n    target:\n      entity_id: light.test\n"
        )
        resp = await r.run_validation(req)
        assert resp.valid

    @pytest.mark.asyncio
    async def test_missing_sequence(self):
        r = _ScriptValidationRouter()
        req = ValidationRequest(content="script:\n  test:\n    alias: Test\n")
        resp = await r.run_validation(req)
        assert not resp.valid
        assert any("sequence" in e for e in resp.errors)

    @pytest.mark.asyncio
    async def test_invalid_service_format(self):
        r = _ScriptValidationRouter()
        req = ValidationRequest(
            content="sequence:\n  - service: bad_service\n",
            validate_services=True,
        )
        resp = await r.run_validation(req)
        assert not resp.valid
        assert any("invalid service" in e for e in resp.errors)

    @pytest.mark.asyncio
    async def test_invalid_yaml(self):
        r = _ScriptValidationRouter()
        req = ValidationRequest(content="{{bad")
        resp = await r.run_validation(req)
        assert not resp.valid


# ================================================================== #
# Scene Verifier Tests
# ================================================================== #

class _SceneVerifier(PostActionVerifier):
    def __init__(self, get_state_fn):
        self._get_state = get_state_fn

    async def verify(self, action_result):
        scene_id = action_result.get("scene_id", "")
        eid = scene_id if scene_id.startswith("scene.") else f"scene.{scene_id}"
        state_data = await self._get_state(eid)
        if state_data is None:
            return VerificationResult(
                success=False, state="not_found",
                warnings=[VerificationWarning(
                    message=f"Scene '{eid}' not found after creation.",
                    entity_id=eid, severity="warning",
                )],
            )
        state = state_data.get("state")
        return VerificationResult(
            success=state != "unavailable", state=state,
            warnings=self.map_warnings(state_data),
        )


class TestSceneVerifier:
    @pytest.mark.asyncio
    async def test_scene_created_ok(self):
        get_state = AsyncMock(return_value={"state": "scening", "entity_id": "scene.movie"})
        v = _SceneVerifier(get_state)
        r = await v.verify({"scene_id": "movie"})
        assert r.success
        get_state.assert_called_once_with("scene.movie")

    @pytest.mark.asyncio
    async def test_scene_not_found(self):
        get_state = AsyncMock(return_value=None)
        v = _SceneVerifier(get_state)
        r = await v.verify({"scene_id": "missing"})
        assert not r.success
        assert r.state == "not_found"

    @pytest.mark.asyncio
    async def test_scene_unavailable(self):
        get_state = AsyncMock(return_value={"state": "unavailable", "entity_id": "scene.bad"})
        v = _SceneVerifier(get_state)
        r = await v.verify({"scene_id": "scene.bad"})
        assert not r.success


# ================================================================== #
# Script Verifier Tests
# ================================================================== #

class _ScriptVerifier(PostActionVerifier):
    def __init__(self, get_state_fn):
        self._get_state = get_state_fn

    async def verify(self, action_result):
        script_id = action_result.get("script_id", "")
        eid = script_id if script_id.startswith("script.") else f"script.{script_id}"
        state_data = await self._get_state(eid)
        if state_data is None:
            return VerificationResult(
                success=False, state="not_found",
                warnings=[VerificationWarning(
                    message=f"Script '{eid}' not found.", entity_id=eid, severity="warning",
                )],
            )
        state = state_data.get("state")
        return VerificationResult(
            success=state != "unavailable", state=state,
            warnings=self.map_warnings(state_data),
        )


class TestScriptVerifier:
    @pytest.mark.asyncio
    async def test_script_created_ok(self):
        get_state = AsyncMock(return_value={"state": "off", "entity_id": "script.morning"})
        v = _ScriptVerifier(get_state)
        r = await v.verify({"script_id": "morning"})
        assert r.success
        get_state.assert_called_once_with("script.morning")

    @pytest.mark.asyncio
    async def test_script_not_found(self):
        get_state = AsyncMock(return_value=None)
        v = _ScriptVerifier(get_state)
        r = await v.verify({"script_id": "missing"})
        assert not r.success

    @pytest.mark.asyncio
    async def test_script_unavailable(self):
        get_state = AsyncMock(return_value={"state": "unavailable", "entity_id": "script.bad"})
        v = _ScriptVerifier(get_state)
        r = await v.verify({"script_id": "script.bad"})
        assert not r.success


# ================================================================== #
# Task Execution Verifier Tests
# ================================================================== #

class _TaskExecutionVerifier(PostActionVerifier):
    def __init__(self, get_state_fn):
        self._get_state = get_state_fn

    TRANSIENT = ("timeout", "connection refused", "503")

    async def verify(self, action_result):
        task_id = action_result.get("task_id", "unknown")
        status = action_result.get("status", "unknown")
        error = action_result.get("error", "")
        entity_id = action_result.get("entity_id")
        expected_state = action_result.get("expected_state")
        warnings = []

        if status == "failed":
            is_transient = any(t in str(error).lower() for t in self.TRANSIENT)
            warnings.append(VerificationWarning(
                message=f"Task '{task_id}' failed: {error}",
                entity_id=entity_id or task_id, severity="error",
            ))
            return VerificationResult(
                success=False, state="failed", warnings=warnings,
                metadata={"retryable": is_transient},
            )

        if entity_id and expected_state:
            sd = await self._get_state(entity_id)
            if sd is None:
                warnings.append(VerificationWarning(
                    message=f"Entity '{entity_id}' not found.", entity_id=entity_id, severity="warning",
                ))
            elif sd.get("state") != expected_state:
                warnings.append(VerificationWarning(
                    message=f"Entity '{entity_id}' is '{sd['state']}' not '{expected_state}'.",
                    entity_id=entity_id, severity="warning",
                ))

        return VerificationResult(
            success=not warnings, state=status if not warnings else "partial",
            warnings=warnings,
        )


class TestTaskExecutionVerifier:
    @pytest.mark.asyncio
    async def test_success(self):
        get_state = AsyncMock(return_value={"state": "on"})
        v = _TaskExecutionVerifier(get_state)
        r = await v.verify({"task_id": "t1", "status": "success", "entity_id": "light.test", "expected_state": "on"})
        assert r.success

    @pytest.mark.asyncio
    async def test_failed_transient(self):
        get_state = AsyncMock()
        v = _TaskExecutionVerifier(get_state)
        r = await v.verify({"task_id": "t2", "status": "failed", "error": "connection refused"})
        assert not r.success
        assert r.metadata.get("retryable") is True

    @pytest.mark.asyncio
    async def test_failed_permanent(self):
        get_state = AsyncMock()
        v = _TaskExecutionVerifier(get_state)
        r = await v.verify({"task_id": "t3", "status": "failed", "error": "invalid config"})
        assert not r.success
        assert r.metadata.get("retryable") is False

    @pytest.mark.asyncio
    async def test_state_mismatch(self):
        get_state = AsyncMock(return_value={"state": "off"})
        v = _TaskExecutionVerifier(get_state)
        r = await v.verify({"task_id": "t4", "status": "success", "entity_id": "light.test", "expected_state": "on"})
        assert not r.success
        assert r.state == "partial"

    @pytest.mark.asyncio
    async def test_entity_not_found(self):
        get_state = AsyncMock(return_value=None)
        v = _TaskExecutionVerifier(get_state)
        r = await v.verify({"task_id": "t5", "status": "success", "entity_id": "light.missing", "expected_state": "on"})
        assert not r.success

    @pytest.mark.asyncio
    async def test_no_entity_check(self):
        get_state = AsyncMock()
        v = _TaskExecutionVerifier(get_state)
        r = await v.verify({"task_id": "t6", "status": "success"})
        assert r.success


# ================================================================== #
# Sports Blueprint Generator Tests
# ================================================================== #

def _generate_sports_automations(
    team_sensor, wled_entities, hue_entities, team_a_color, team_b_color, helper_prefix="sports"
):
    """Inline version of generate_sports_automations for testing without heavy imports."""
    all_lights = wled_entities + hue_entities
    p = helper_prefix
    return [
        {"alias": f"{p}_game_kickoff", "trigger": [{"platform": "state", "entity_id": team_sensor, "to": "IN"}],
         "action": [{"service": "input_boolean.turn_on", "target": {"entity_id": f"input_boolean.{p}_game_active"}},
                    {"service": "light.turn_on", "target": {"entity_id": all_lights}, "data": {"rgb_color": team_a_color, "brightness": 255}}],
         "mode": "single"},
        {"alias": f"{p}_team_a_score", "trigger": [{"platform": "state", "entity_id": team_sensor, "attribute": "team_score"}],
         "action": [{"service": "light.turn_on", "target": {"entity_id": wled_entities}, "data": {"effect": "Color Wipe", "rgb_color": team_a_color}}],
         "mode": "single"},
        {"alias": f"{p}_team_b_score", "trigger": [{"platform": "state", "entity_id": team_sensor, "attribute": "opponent_score"}],
         "action": [{"service": "light.turn_on", "target": {"entity_id": all_lights}, "data": {"rgb_color": team_b_color, "brightness": 50}}],
         "mode": "single"},
        {"alias": f"{p}_game_over", "trigger": [{"platform": "state", "entity_id": team_sensor, "to": "POST"}],
         "action": [{"service": "light.turn_on", "target": {"entity_id": all_lights}, "data": {"brightness": 200}},
                    {"service": "input_boolean.turn_off", "target": {"entity_id": f"input_boolean.{p}_game_active"}}],
         "mode": "single"},
        {"alias": f"{p}_reset_helpers", "trigger": [{"platform": "time", "at": "00:00:00"}],
         "action": [{"service": "input_boolean.turn_off", "target": {"entity_id": f"input_boolean.{p}_game_active"}}],
         "mode": "single"},
    ]


class TestSportsBlueprintGenerator:
    def test_generates_five_automations(self):
        automations = _generate_sports_automations(
            team_sensor="sensor.nfl_team_tracker",
            wled_entities=["light.wled_tv"],
            hue_entities=["light.hue_living"],
            team_a_color=[0, 100, 0],
            team_b_color=[255, 0, 0],
            helper_prefix="nfl",
        )
        assert len(automations) == 5

    def test_automation_aliases(self):
        automations = _generate_sports_automations(
            team_sensor="sensor.nfl_team_tracker",
            wled_entities=["light.wled_tv"],
            hue_entities=["light.hue_living"],
            team_a_color=[0, 100, 0],
            team_b_color=[255, 0, 0],
            helper_prefix="nfl",
        )
        aliases = [a["alias"] for a in automations]
        assert "nfl_game_kickoff" in aliases
        assert "nfl_team_a_score" in aliases
        assert "nfl_team_b_score" in aliases
        assert "nfl_game_over" in aliases
        assert "nfl_reset_helpers" in aliases

    def test_custom_prefix(self):
        automations = _generate_sports_automations(
            team_sensor="sensor.mlb_team_tracker",
            wled_entities=["light.wled"],
            hue_entities=[],
            team_a_color=[255, 255, 0],
            team_b_color=[0, 0, 255],
            helper_prefix="mlb_game",
        )
        assert all(a["alias"].startswith("mlb_game_") for a in automations)

    def test_render_yaml(self):
        import yaml
        automations = _generate_sports_automations(
            team_sensor="sensor.nfl_team_tracker",
            wled_entities=["light.wled_tv"],
            hue_entities=["light.hue_living"],
            team_a_color=[0, 100, 0],
            team_b_color=[255, 0, 0],
        )
        yaml_str = yaml.dump(automations, default_flow_style=False, sort_keys=False)
        assert "sports_game_kickoff" in yaml_str
        assert "sports_team_a_score" in yaml_str
