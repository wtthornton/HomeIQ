"""Tests for RAG keyword disambiguation (Story 4).

Tests cover:
- False positive elimination: ambiguous words no longer trigger wrong domains
- Legitimate triggers still work: domain-specific multi-word phrases trigger correctly
- min_score thresholds per service
"""

import importlib.util
import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parents[3])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Load RAG service modules directly (avoid __init__.py import chain)
_agent_services = Path(__file__).resolve().parents[3] / "domains" / "automation-core" / "ha-ai-agent-service" / "src" / "services"


def _load_module(name: str):
    spec = importlib.util.spec_from_file_location(name, _agent_services / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_security_mod = _load_module("security_rag_service")
_comfort_mod = _load_module("comfort_rag_service")
_automation_mod = _load_module("automation_rag_service")
_energy_mod = _load_module("energy_rag_service")

SecurityRAGService = _security_mod.SecurityRAGService
ComfortRAGService = _comfort_mod.ComfortRAGService
AutomationRAGService = _automation_mod.AutomationRAGService
EnergyRAGService = _energy_mod.EnergyRAGService


# --- Security RAG Disambiguation ---

class TestSecurityDisambiguation:
    def setup_method(self):
        self.service = SecurityRAGService()

    def test_motion_pictures_no_trigger(self):
        """'motion pictures' should NOT trigger security RAG."""
        assert not self.service.detect_intent("I enjoy watching motion pictures")

    def test_motion_sensor_triggers(self):
        """'motion sensor' should trigger security RAG."""
        assert self.service.detect_intent("when the motion sensor detects someone")

    def test_motion_detected_triggers(self):
        """'motion detected' should trigger security RAG."""
        assert self.service.detect_intent("alert me when motion detected in garage")

    def test_alarm_still_triggers(self):
        """'alarm' keyword still works as before."""
        assert self.service.detect_intent("arm the alarm when I leave home")

    def test_lock_still_triggers(self):
        """'lock' keyword still works as before."""
        assert self.service.detect_intent("auto-lock the front door at night")

    def test_min_score_set(self):
        """Security service should have min_score = 0.2."""
        assert self.service.min_score == 0.2


# --- Comfort RAG Disambiguation ---

class TestComfortDisambiguation:
    def setup_method(self):
        self.service = ComfortRAGService()

    def test_cool_app_no_trigger(self):
        """'cool app' should NOT trigger comfort RAG."""
        assert not self.service.detect_intent("that's a really cool app")

    def test_cool_down_triggers(self):
        """'cool down' should trigger comfort RAG."""
        assert self.service.detect_intent("cool down the living room")

    def test_cooling_mode_triggers(self):
        """'cooling mode' should trigger comfort RAG."""
        assert self.service.detect_intent("switch to cooling mode when it's hot")

    def test_thermostat_still_triggers(self):
        """'thermostat' keyword still works as before."""
        assert self.service.detect_intent("set the thermostat to 72")

    def test_temperature_still_triggers(self):
        """'temperature' keyword still works as before."""
        assert self.service.detect_intent("what's the temperature in the bedroom")


# --- Sports RAG Disambiguation ---

class TestSportsDisambiguation:
    def setup_method(self):
        self.service = AutomationRAGService()

    def test_credit_score_no_trigger(self):
        """'credit score' should NOT trigger sports RAG."""
        assert not self.service.detect_intent("check my credit score")

    def test_score_flash_triggers(self):
        """'score flash' should trigger sports RAG."""
        assert self.service.detect_intent("flash lights when team scores a touchdown")

    def test_team_tracker_triggers(self):
        """'team tracker' keyword still works."""
        assert self.service.detect_intent("set up team tracker for NFL")

    def test_nfl_still_triggers(self):
        """League names still work."""
        assert self.service.detect_intent("flash lights when the NFL game starts")

    def test_min_score_set(self):
        """Sports service should have min_score = 0.3."""
        assert self.service.min_score == 0.3


# --- Energy RAG Disambiguation ---

class TestEnergyDisambiguation:
    def setup_method(self):
        self.service = EnergyRAGService()

    def test_charge_phone_no_trigger(self):
        """'charge your phone' should NOT trigger energy RAG."""
        assert not self.service.detect_intent("don't forget to charge your phone")

    def test_charge_ev_triggers(self):
        """'charge the ev' should trigger energy RAG."""
        assert self.service.detect_intent("charge the ev when electricity is cheap")

    def test_solar_still_triggers(self):
        """'solar' keyword still works as before."""
        assert self.service.detect_intent("show solar production for today")

    def test_battery_still_triggers(self):
        """'battery' keyword still works as before."""
        assert self.service.detect_intent("what's the battery state of charge")

    def test_ev_charging_still_triggers(self):
        """'ev charging' keyword still works."""
        assert self.service.detect_intent("schedule ev charging for off-peak")
