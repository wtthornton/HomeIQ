"""Tests for Prompt Generation Service"""

from __future__ import annotations

import pytest

from src.services.prompt_generation_service import PromptGenerationService


@pytest.fixture
def prompt_service():
    """Create PromptGenerationService instance"""
    return PromptGenerationService()


def test_generate_weather_prompts_high_temperature(prompt_service):
    """Test weather prompt generation for high temperature"""
    weather_data = {
        "available": True,
        "current": {"temperature": 90, "condition": "sunny"},
        "forecast": [],
    }

    prompts = prompt_service._generate_weather_prompts(weather_data)

    assert len(prompts) > 0
    assert any("pre-cool" in p["prompt"].lower() for p in prompts)
    assert prompts[0]["context_type"] == "weather"


def test_generate_weather_prompts_low_temperature(prompt_service):
    """Test weather prompt generation for low temperature"""
    weather_data = {
        "available": True,
        "current": {"temperature": 40, "condition": "cloudy"},
        "forecast": [],
    }

    prompts = prompt_service._generate_weather_prompts(weather_data)

    assert len(prompts) > 0
    assert any("pre-heat" in p["prompt"].lower() for p in prompts)


def test_generate_weather_prompts_rainy(prompt_service):
    """Test weather prompt generation for rainy conditions"""
    weather_data = {
        "available": True,
        "current": {"temperature": 65, "condition": "rainy"},
        "forecast": [],
    }

    prompts = prompt_service._generate_weather_prompts(weather_data)

    assert len(prompts) > 0
    assert any("rain" in p["prompt"].lower() for p in prompts)


def test_generate_weather_prompts_unavailable(prompt_service):
    """Test weather prompt generation when data unavailable"""
    weather_data = {"available": False}

    prompts = prompt_service._generate_weather_prompts(weather_data)

    assert len(prompts) == 0


def test_generate_sports_prompts_upcoming_game(prompt_service):
    """Test sports prompt generation for upcoming game"""
    sports_data = {
        "available": True,
        "upcoming_games": [{"team": "Lakers", "time": "19:00"}],
        "live_games": [],
    }

    prompts = prompt_service._generate_sports_prompts(sports_data)

    assert len(prompts) > 0
    assert any("tonight" in p["prompt"].lower() for p in prompts)
    assert prompts[0]["context_type"] == "sports"


def test_generate_sports_prompts_live_game(prompt_service):
    """Test sports prompt generation for live game"""
    sports_data = {
        "available": True,
        "upcoming_games": [],
        "live_games": [{"team": "Warriors", "status": "live"}],
    }

    prompts = prompt_service._generate_sports_prompts(sports_data)

    assert len(prompts) > 0
    assert any("right now" in p["prompt"].lower() for p in prompts)


def test_generate_energy_prompts_low_carbon(prompt_service):
    """Test energy prompt generation for low carbon intensity"""
    energy_data = {
        "available": True,
        "current_intensity": {"intensity": 150},
    }

    prompts = prompt_service._generate_energy_prompts(energy_data)

    assert len(prompts) > 0
    assert any("low" in p["prompt"].lower() for p in prompts)
    assert prompts[0]["context_type"] == "energy"


def test_generate_energy_prompts_high_carbon(prompt_service):
    """Test energy prompt generation for high carbon intensity"""
    energy_data = {
        "available": True,
        "current_intensity": {"intensity": 450},
    }

    prompts = prompt_service._generate_energy_prompts(energy_data)

    assert len(prompts) > 0
    assert any("high" in p["prompt"].lower() for p in prompts)


def test_generate_pattern_prompts_frequent_entity(prompt_service):
    """Test pattern prompt generation for frequent entity"""
    historical_data = {
        "available": True,
        "patterns": [
            {
                "type": "frequent_entities",
                "entities": [{"entity_id": "light.living_room", "count": 10}],
            }
        ],
        "insights": [],
    }

    prompts = prompt_service._generate_pattern_prompts(historical_data)

    assert len(prompts) > 0
    assert any("frequently" in p["prompt"].lower() for p in prompts)
    assert prompts[0]["context_type"] == "historical_pattern"


def test_generate_pattern_prompts_peak_hours(prompt_service):
    """Test pattern prompt generation for peak hours"""
    historical_data = {
        "available": True,
        "patterns": [
            {
                "type": "peak_hours",
                "hours": [{"hour": 18, "count": 15}],
            }
        ],
        "insights": [],
    }

    prompts = prompt_service._generate_pattern_prompts(historical_data)

    assert len(prompts) > 0
    assert any("peak activity" in p["prompt"].lower() for p in prompts)


def test_score_prompt(prompt_service):
    """Test prompt scoring"""
    prompt_data = {
        "prompt": "This is a good prompt with appropriate length for testing purposes.",
        "context_type": "weather",
        "metadata": {"temperature": 75, "trigger": "test"},
    }

    scored = prompt_service._score_prompt(prompt_data)

    assert "quality_score" in scored
    assert 0.0 <= scored["quality_score"] <= 1.0


def test_generate_prompts_comprehensive(prompt_service):
    """Test comprehensive prompt generation"""
    context_analysis = {
        "weather": {
            "available": True,
            "current": {"temperature": 90, "condition": "sunny"},
            "forecast": [],
        },
        "sports": {
            "available": True,
            "upcoming_games": [{"team": "Lakers", "time": "19:00"}],
            "live_games": [],
        },
        "energy": {
            "available": True,
            "current_intensity": {"intensity": 150},
        },
        "historical_patterns": {
            "available": True,
            "patterns": [
                {
                    "type": "frequent_entities",
                    "entities": [{"entity_id": "light.living_room", "count": 10}],
                }
            ],
            "insights": [],
        },
    }

    prompts = prompt_service.generate_prompts(context_analysis, max_prompts=5)

    assert len(prompts) > 0
    assert len(prompts) <= 5
    assert all("prompt" in p for p in prompts)
    assert all("quality_score" in p for p in prompts)
    # Should be sorted by quality score
    scores = [p["quality_score"] for p in prompts]
    assert scores == sorted(scores, reverse=True)


def test_generate_prompts_max_limit(prompt_service):
    """Test that max_prompts limit is respected"""
    context_analysis = {
        "weather": {
            "available": True,
            "current": {"temperature": 90, "condition": "sunny"},
            "forecast": [{"temperature": 95}],
        },
        "sports": {"available": False},
        "energy": {"available": False},
        "historical_patterns": {"available": False},
    }

    prompts = prompt_service.generate_prompts(context_analysis, max_prompts=2)

    assert len(prompts) <= 2

