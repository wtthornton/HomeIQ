"""
Tests for Epic 3 (Phase 4): Platform-Wide Pattern Rollout — RAG Services

Tests for SecurityRAGService, ComfortRAGService, SceneScriptRAGService,
DeviceCapabilityRAGService.
"""

import pytest
from pathlib import Path
import sys

_project_root = str(Path(__file__).resolve().parents[3])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from homeiq_patterns import RAGContextService, RAGContextRegistry


# ------------------------------------------------------------------ #
# Inline test implementations
# ------------------------------------------------------------------ #

class _SecurityRAG(RAGContextService):
    name = "security"
    keywords = (
        "camera", "alarm", "lock", "doorbell", "siren", "motion", "presence",
        "person", "arm", "disarm", "intrusion", "geofence", "away mode",
        "nobody home", "security",
    )
    corpus_path = None

    def load_corpus(self) -> str:
        self._corpus_cache = (
            "Alert when motion detected and nobody is home. "
            "Auto-lock doors after timeout. "
            "Arm alarm when everyone leaves."
        )
        return self._corpus_cache


class _ComfortRAG(RAGContextService):
    name = "comfort"
    keywords = (
        "thermostat", "hvac", "heat", "cool", "climate", "temperature",
        "humidity", "setpoint", "fan", "schedule", "eco mode", "comfort",
        "away mode thermostat", "zone",
    )
    corpus_path = None

    def load_corpus(self) -> str:
        self._corpus_cache = (
            "Set thermostat schedule for weekdays. "
            "Pause HVAC when window opens. "
            "Away mode when nobody home."
        )
        return self._corpus_cache


class _SceneScriptRAG(RAGContextService):
    name = "scene_script"
    keywords = (
        "scene", "script", "movie night", "morning routine", "bedtime",
        "good night", "sequence", "workflow", "turn_on", "turn_off",
    )
    corpus_path = None

    def load_corpus(self) -> str:
        self._corpus_cache = (
            "Movie night scene: dim lights, close blinds. "
            "Morning routine script: gradual lights, open blinds. "
            "Bedtime scene: all lights off except bedroom dim."
        )
        return self._corpus_cache


class _DeviceCapabilityRAG(RAGContextService):
    name = "device_capability"
    keywords = (
        "wled", "effect_list", "segment", "hue scene", "smart plug",
        "power monitoring", "sonoff", "shelly", "tasmota", "esphome",
        "cover", "blind", "media_player", "tts",
    )
    corpus_path = None

    def load_corpus(self) -> str:
        self._corpus_cache = (
            "WLED supports effect_list with Rainbow, Fire, Police effects. "
            "Smart plugs expose power monitoring sensors. "
            "Hue scenes use hue.activate_scene service."
        )
        return self._corpus_cache


# ================================================================== #
# SecurityRAGService Tests
# ================================================================== #

class TestSecurityRAGService:
    def test_detect_intent_security(self):
        svc = _SecurityRAG()
        assert svc.detect_intent("alert me when motion detected and nobody home")
        assert svc.detect_intent("lock the door when I leave")
        assert svc.detect_intent("arm alarm when everyone leaves")

    def test_detect_intent_camera(self):
        svc = _SecurityRAG()
        assert svc.detect_intent("take camera snapshot when doorbell rings")

    def test_detect_intent_no_match(self):
        svc = _SecurityRAG()
        assert not svc.detect_intent("set thermostat to 22")
        assert not svc.detect_intent("play music in kitchen")

    def test_detect_intent_geofence(self):
        svc = _SecurityRAG()
        assert svc.detect_intent("geofence trigger when I leave home")

    @pytest.mark.asyncio
    async def test_get_context_match(self):
        svc = _SecurityRAG()
        result = await svc.get_context("motion alarm when nobody home")
        assert "RAG CONTEXT" in result
        assert "motion" in result.lower()

    @pytest.mark.asyncio
    async def test_get_context_no_match(self):
        svc = _SecurityRAG()
        result = await svc.get_context("what is the weather")
        assert result == ""


# ================================================================== #
# ComfortRAGService Tests
# ================================================================== #

class TestComfortRAGService:
    def test_detect_intent_thermostat(self):
        svc = _ComfortRAG()
        assert svc.detect_intent("set thermostat schedule for winter")
        assert svc.detect_intent("hvac away mode when nobody home")

    def test_detect_intent_climate(self):
        svc = _ComfortRAG()
        assert svc.detect_intent("climate control for bedroom")
        assert svc.detect_intent("temperature too hot in kitchen")

    def test_detect_intent_humidity(self):
        svc = _ComfortRAG()
        assert svc.detect_intent("turn on dehumidifier when humidity high")

    def test_detect_intent_no_match(self):
        svc = _ComfortRAG()
        assert not svc.detect_intent("turn on security camera")
        assert not svc.detect_intent("play music")

    @pytest.mark.asyncio
    async def test_get_context_match(self):
        svc = _ComfortRAG()
        result = await svc.get_context("thermostat schedule weekday")
        assert "RAG CONTEXT" in result

    @pytest.mark.asyncio
    async def test_get_context_no_match(self):
        svc = _ComfortRAG()
        result = await svc.get_context("lock the door")
        assert result == ""


# ================================================================== #
# SceneScriptRAGService Tests
# ================================================================== #

class TestSceneScriptRAGService:
    def test_detect_intent_scene(self):
        svc = _SceneScriptRAG()
        assert svc.detect_intent("create a movie night scene")
        assert svc.detect_intent("activate good night scene")

    def test_detect_intent_script(self):
        svc = _SceneScriptRAG()
        assert svc.detect_intent("create a morning routine script")
        assert svc.detect_intent("run the bedtime script")

    def test_detect_intent_workflow(self):
        svc = _SceneScriptRAG()
        assert svc.detect_intent("create a workflow with sequence of steps")

    def test_detect_intent_no_match(self):
        svc = _SceneScriptRAG()
        assert not svc.detect_intent("set thermostat to 22")
        assert not svc.detect_intent("pair zigbee device")

    @pytest.mark.asyncio
    async def test_get_context_match(self):
        svc = _SceneScriptRAG()
        result = await svc.get_context("movie night scene for living room")
        assert "RAG CONTEXT" in result

    @pytest.mark.asyncio
    async def test_get_context_no_match(self):
        svc = _SceneScriptRAG()
        result = await svc.get_context("check solar production")
        assert result == ""


# ================================================================== #
# DeviceCapabilityRAGService Tests
# ================================================================== #

class TestDeviceCapabilityRAGService:
    def test_detect_intent_wled(self):
        svc = _DeviceCapabilityRAG()
        assert svc.detect_intent("set WLED strip to rainbow effect")
        assert svc.detect_intent("configure wled segment colors")

    def test_detect_intent_smart_plug(self):
        svc = _DeviceCapabilityRAG()
        assert svc.detect_intent("smart plug power monitoring alert")

    def test_detect_intent_covers(self):
        svc = _DeviceCapabilityRAG()
        assert svc.detect_intent("close blind when sun is high")
        assert svc.detect_intent("cover position at 50%")

    def test_detect_intent_media(self):
        svc = _DeviceCapabilityRAG()
        assert svc.detect_intent("play tts announcement on speaker")

    def test_detect_intent_esphome(self):
        svc = _DeviceCapabilityRAG()
        assert svc.detect_intent("flash esphome device firmware")

    def test_detect_intent_no_match(self):
        svc = _DeviceCapabilityRAG()
        assert not svc.detect_intent("lock the door at night")
        assert not svc.detect_intent("what time is it")

    @pytest.mark.asyncio
    async def test_get_context_match(self):
        svc = _DeviceCapabilityRAG()
        result = await svc.get_context("wled effect_list rainbow")
        assert "RAG CONTEXT" in result

    @pytest.mark.asyncio
    async def test_get_context_no_match(self):
        svc = _DeviceCapabilityRAG()
        result = await svc.get_context("arm alarm system")
        assert result == ""


# ================================================================== #
# Registry Integration — All Phase 4 RAG Services
# ================================================================== #

class TestRegistryPhase4:
    @pytest.mark.asyncio
    async def test_security_only(self):
        reg = RAGContextRegistry()
        reg.register(_SecurityRAG())
        reg.register(_ComfortRAG())
        reg.register(_SceneScriptRAG())
        reg.register(_DeviceCapabilityRAG())
        ctx = await reg.get_all_context("arm alarm when away")
        assert len(ctx) == 1

    @pytest.mark.asyncio
    async def test_comfort_only(self):
        reg = RAGContextRegistry()
        reg.register(_SecurityRAG())
        reg.register(_ComfortRAG())
        ctx = await reg.get_all_context("thermostat schedule for weekdays")
        assert len(ctx) == 1

    @pytest.mark.asyncio
    async def test_no_match(self):
        reg = RAGContextRegistry()
        reg.register(_SecurityRAG())
        reg.register(_ComfortRAG())
        reg.register(_SceneScriptRAG())
        reg.register(_DeviceCapabilityRAG())
        ctx = await reg.get_all_context("what is 2+2")
        assert len(ctx) == 0

    @pytest.mark.asyncio
    async def test_multi_domain_comfort_and_scene(self):
        reg = RAGContextRegistry()
        reg.register(_ComfortRAG())
        reg.register(_SceneScriptRAG())
        # "bedtime" triggers scene_script, "thermostat" triggers comfort
        ctx = await reg.get_all_context("bedtime thermostat schedule")
        assert len(ctx) == 2
