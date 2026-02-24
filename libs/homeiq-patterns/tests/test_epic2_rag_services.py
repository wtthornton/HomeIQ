"""
Tests for Epic 2: High-Value Domain Extensions — RAG Services

Tests for EnergyRAGService, BlueprintRAGService, DeviceSetupRAGService.
"""

import pytest
from pathlib import Path
import sys

_project_root = str(Path(__file__).resolve().parents[3])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Add ha-ai-agent-service to path for the RAG service imports
_agent_service_root = str(
    Path(__file__).resolve().parents[3] / "services" / "ha-ai-agent-service" / "src"
)
if _agent_service_root not in sys.path:
    sys.path.insert(0, _agent_service_root)

from homeiq_patterns import RAGContextService, RAGContextRegistry


# ------------------------------------------------------------------ #
# Inline test implementations (avoid importing full service modules
# which have heavy dependencies). These mirror the real classes.
# ------------------------------------------------------------------ #

class _EnergyRAG(RAGContextService):
    name = "energy"
    keywords = (
        "electricity", "solar", "battery", "tou", "time-of-use", "peak",
        "off-peak", "kwh", "ev charging", "load shift", "demand",
        "smart meter", "grid", "charge", "discharge",
    )
    corpus_path = None

    def load_corpus(self) -> str:
        self._corpus_cache = (
            "Shift load to off-peak hours. Use solar surplus for battery charging. "
            "Schedule EV charging during off-peak window."
        )
        return self._corpus_cache


class _BlueprintRAG(RAGContextService):
    name = "blueprint"
    keywords = (
        "blueprint", "template", "prebuilt", "pre-built", "starter",
        "ready-made", "import blueprint", "suggest blueprint",
    )
    corpus_path = None

    def load_corpus(self) -> str:
        self._corpus_cache = (
            "Match blueprint inputs to available entities. "
            "Verify device domain and device_class match selector requirements."
        )
        return self._corpus_cache


class _DeviceSetupRAG(RAGContextService):
    name = "device_setup"
    keywords = (
        "zigbee", "z-wave", "zwave", "hue", "mqtt", "matter", "thread",
        "pairing", "setup", "set up", "configure", "add device", "discover",
        "zigbee2mqtt", "inclusion", "commissioning",
    )
    corpus_path = None

    def load_corpus(self) -> str:
        self._corpus_cache = (
            "Enable permit join for Zigbee pairing. "
            "Press bridge button for Hue setup. "
            "Use secure inclusion for Z-Wave."
        )
        return self._corpus_cache


# ================================================================== #
# EnergyRAGService Tests
# ================================================================== #

class TestEnergyRAGService:
    def test_detect_intent_solar(self):
        svc = _EnergyRAG()
        assert svc.detect_intent("Shift laundry to off-peak hours")
        assert svc.detect_intent("charge battery when solar is high")
        assert svc.detect_intent("schedule ev charging overnight")

    def test_detect_intent_no_match(self):
        svc = _EnergyRAG()
        assert not svc.detect_intent("Turn on the kitchen lights")
        assert not svc.detect_intent("Play music in the living room")

    def test_detect_intent_case_insensitive(self):
        svc = _EnergyRAG()
        assert svc.detect_intent("SOLAR panel production")
        assert svc.detect_intent("TOU rate schedule")

    def test_load_corpus(self):
        svc = _EnergyRAG()
        corpus = svc.load_corpus()
        assert "off-peak" in corpus
        assert "solar" in corpus

    @pytest.mark.asyncio
    async def test_get_context_match(self):
        svc = _EnergyRAG()
        result = await svc.get_context("shift laundry to off-peak hours")
        assert "off-peak" in result
        assert "RAG CONTEXT" in result

    @pytest.mark.asyncio
    async def test_get_context_no_match(self):
        svc = _EnergyRAG()
        result = await svc.get_context("turn on bedroom lights")
        assert result == ""

    def test_keywords_comprehensive(self):
        svc = _EnergyRAG()
        must_match = [
            "electricity bill", "solar panel output", "battery charge",
            "tou schedule", "off-peak pricing", "ev charging schedule",
            "load shift strategy", "smart meter reading", "grid export",
            "demand response",
        ]
        for prompt in must_match:
            assert svc.detect_intent(prompt), f"Should match: {prompt}"


# ================================================================== #
# BlueprintRAGService Tests
# ================================================================== #

class TestBlueprintRAGService:
    def test_detect_intent_blueprint(self):
        svc = _BlueprintRAG()
        assert svc.detect_intent("suggest blueprints for my Hue lights")
        assert svc.detect_intent("import a blueprint for motion lighting")
        assert svc.detect_intent("use a prebuilt template")

    def test_detect_intent_no_match(self):
        svc = _BlueprintRAG()
        assert not svc.detect_intent("turn on the kitchen lights")
        assert not svc.detect_intent("create an automation for motion")

    def test_detect_intent_case_insensitive(self):
        svc = _BlueprintRAG()
        assert svc.detect_intent("BLUEPRINT for lighting")
        assert svc.detect_intent("Pre-Built automation")

    def test_load_corpus(self):
        svc = _BlueprintRAG()
        corpus = svc.load_corpus()
        assert "blueprint" in corpus.lower() or "selector" in corpus.lower()

    @pytest.mark.asyncio
    async def test_get_context_match(self):
        svc = _BlueprintRAG()
        result = await svc.get_context("suggest blueprint for motion sensor")
        assert "RAG CONTEXT" in result

    @pytest.mark.asyncio
    async def test_get_context_no_match(self):
        svc = _BlueprintRAG()
        result = await svc.get_context("set thermostat to 22")
        assert result == ""

    def test_keywords_comprehensive(self):
        svc = _BlueprintRAG()
        must_match = [
            "blueprint exchange", "starter automation", "ready-made",
            "pre-built template", "suggest blueprint",
        ]
        for prompt in must_match:
            assert svc.detect_intent(prompt), f"Should match: {prompt}"


# ================================================================== #
# DeviceSetupRAGService Tests
# ================================================================== #

class TestDeviceSetupRAGService:
    def test_detect_intent_zigbee(self):
        svc = _DeviceSetupRAG()
        assert svc.detect_intent("how do I add Zigbee devices")
        assert svc.detect_intent("pair a new zigbee2mqtt sensor")

    def test_detect_intent_hue(self):
        svc = _DeviceSetupRAG()
        assert svc.detect_intent("setup Hue bridge")
        assert svc.detect_intent("pair new Hue lights")

    def test_detect_intent_zwave(self):
        svc = _DeviceSetupRAG()
        assert svc.detect_intent("add Z-Wave device")
        assert svc.detect_intent("zwave inclusion mode")

    def test_detect_intent_mqtt(self):
        svc = _DeviceSetupRAG()
        assert svc.detect_intent("configure mqtt broker")

    def test_detect_intent_matter(self):
        svc = _DeviceSetupRAG()
        assert svc.detect_intent("commission matter device")
        assert svc.detect_intent("thread border router setup")

    def test_detect_intent_no_match(self):
        svc = _DeviceSetupRAG()
        assert not svc.detect_intent("turn on kitchen lights")
        assert not svc.detect_intent("what is the weather")

    def test_detect_intent_troubleshooting(self):
        svc = _DeviceSetupRAG()
        assert svc.detect_intent("pairing failed for my sensor")
        assert svc.detect_intent("add device to network")

    def test_load_corpus(self):
        svc = _DeviceSetupRAG()
        corpus = svc.load_corpus()
        assert "permit join" in corpus or "Zigbee" in corpus

    @pytest.mark.asyncio
    async def test_get_context_match(self):
        svc = _DeviceSetupRAG()
        result = await svc.get_context("how to setup zigbee sensor")
        assert "RAG CONTEXT" in result

    @pytest.mark.asyncio
    async def test_get_context_no_match(self):
        svc = _DeviceSetupRAG()
        result = await svc.get_context("play spotify in living room")
        assert result == ""


# ================================================================== #
# RAGContextRegistry Integration Tests
# ================================================================== #

class TestRAGRegistryWithNewServices:
    @pytest.mark.asyncio
    async def test_energy_only_match(self):
        registry = RAGContextRegistry()
        registry.register(_EnergyRAG())
        registry.register(_BlueprintRAG())
        registry.register(_DeviceSetupRAG())
        contexts = await registry.get_all_context("shift laundry to off-peak")
        assert len(contexts) == 1
        assert "off-peak" in contexts[0]

    @pytest.mark.asyncio
    async def test_blueprint_only_match(self):
        registry = RAGContextRegistry()
        registry.register(_EnergyRAG())
        registry.register(_BlueprintRAG())
        registry.register(_DeviceSetupRAG())
        contexts = await registry.get_all_context("suggest blueprint for motion")
        assert len(contexts) == 1

    @pytest.mark.asyncio
    async def test_device_setup_only_match(self):
        registry = RAGContextRegistry()
        registry.register(_EnergyRAG())
        registry.register(_BlueprintRAG())
        registry.register(_DeviceSetupRAG())
        contexts = await registry.get_all_context("pair my zigbee sensor")
        assert len(contexts) == 1

    @pytest.mark.asyncio
    async def test_no_match_all_services(self):
        registry = RAGContextRegistry()
        registry.register(_EnergyRAG())
        registry.register(_BlueprintRAG())
        registry.register(_DeviceSetupRAG())
        contexts = await registry.get_all_context("what is the weather today")
        assert len(contexts) == 0

    @pytest.mark.asyncio
    async def test_multiple_domain_match(self):
        """Energy + device setup: 'charge' appears in both energy and device setup contexts."""
        registry = RAGContextRegistry()
        registry.register(_EnergyRAG())
        registry.register(_DeviceSetupRAG())
        # 'charge' triggers energy, 'setup' triggers device_setup
        contexts = await registry.get_all_context("charge battery and setup device")
        assert len(contexts) == 2

    @pytest.mark.asyncio
    async def test_merged_context(self):
        registry = RAGContextRegistry()
        registry.register(_EnergyRAG())
        registry.register(_DeviceSetupRAG())
        merged = await registry.get_merged_context("charge battery and setup new device")
        assert "off-peak" in merged
        assert "permit join" in merged or "Zigbee" in merged
