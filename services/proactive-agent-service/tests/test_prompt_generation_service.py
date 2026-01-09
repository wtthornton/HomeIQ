"""Tests for Prompt Generation Service"""

from __future__ import annotations

import pytest

from src.services.prompt_generation_service import PromptGenerationService, celsius_to_fahrenheit


@pytest.fixture
def prompt_service():
    """Create PromptGenerationService instance"""
    return PromptGenerationService()


def test_celsius_to_fahrenheit():
    """Test temperature conversion from Celsius to Fahrenheit"""
    assert celsius_to_fahrenheit(0) == 32
    assert celsius_to_fahrenheit(100) == 212
    assert celsius_to_fahrenheit(-40) == -40
    assert celsius_to_fahrenheit(20) == 68
    # Test rounding
    assert celsius_to_fahrenheit(6.69) == 44  # Was showing as "6.69°F" incorrectly
    assert celsius_to_fahrenheit(7.84) == 46


def test_generate_weather_prompts_high_temperature(prompt_service):
    """Test weather prompt generation for high temperature (Celsius input)"""
    # 35°C = 95°F (hot day)
    weather_data = {
        "available": True,
        "current": {"temperature": 35, "condition": "sunny"},
        "forecast": [],
    }

    prompts = prompt_service._generate_weather_prompts(weather_data)

    assert len(prompts) > 0
    assert any("pre-cooling" in p["prompt"].lower() for p in prompts)
    assert prompts[0]["context_type"] == "weather"
    # Verify conversion: 35°C = 95°F
    assert prompts[0]["metadata"]["temperature_fahrenheit"] == 95


def test_generate_weather_prompts_low_temperature(prompt_service):
    """Test weather prompt generation for low temperature (Celsius input)"""
    # 5°C = 41°F (cold day)
    weather_data = {
        "available": True,
        "current": {"temperature": 5, "condition": "cloudy"},
        "forecast": [],
    }

    prompts = prompt_service._generate_weather_prompts(weather_data)

    assert len(prompts) > 0
    assert any("warm up" in p["prompt"].lower() for p in prompts)
    # Verify conversion: 5°C = 41°F
    assert prompts[0]["metadata"]["temperature_fahrenheit"] == 41


def test_generate_weather_prompts_rainy(prompt_service):
    """Test weather prompt generation for rainy conditions"""
    # 18°C = 64°F (mild day with rain)
    weather_data = {
        "available": True,
        "current": {"temperature": 18, "condition": "rainy"},
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
    assert any("lakers" in p["prompt"].lower() for p in prompts)
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
    assert any("playing now" in p["prompt"].lower() for p in prompts)


def test_generate_energy_prompts_low_carbon(prompt_service):
    """Test energy prompt generation for low carbon intensity"""
    energy_data = {
        "available": True,
        "current_intensity": {"intensity": 150},
    }

    prompts = prompt_service._generate_energy_prompts(energy_data)

    assert len(prompts) > 0
    assert any("clean" in p["prompt"].lower() for p in prompts)
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
    # Now shows friendly name and usage count
    assert any("living room" in p["prompt"].lower() for p in prompts)
    assert any("10 times" in p["prompt"].lower() for p in prompts)
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
    # Now shows formatted time (6 PM)
    assert any("6 pm" in p["prompt"].lower() for p in prompts)
    assert any("busiest" in p["prompt"].lower() for p in prompts)


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
    # Use Celsius temperatures (35°C = 95°F)
    context_analysis = {
        "weather": {
            "available": True,
            "current": {"temperature": 35, "condition": "sunny"},
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
    # Use Celsius temperatures (35°C = 95°F, 37°C = 99°F)
    context_analysis = {
        "weather": {
            "available": True,
            "current": {"temperature": 35, "condition": "sunny"},
            "forecast": [{"temperature": 37}],
        },
        "sports": {"available": False},
        "energy": {"available": False},
        "historical_patterns": {"available": False},
    }

    prompts = prompt_service.generate_prompts(context_analysis, max_prompts=2)

    assert len(prompts) <= 2


def test_temperature_conversion_in_prompts(prompt_service):
    """Test that temperature is properly converted from Celsius to Fahrenheit in prompts"""
    # 6.69°C should become 44°F (not "6.69°F" as was the bug)
    weather_data = {
        "available": True,
        "current": {"temperature": 6.69, "condition": "cloudy"},
        "forecast": [],
    }

    prompts = prompt_service._generate_weather_prompts(weather_data)

    assert len(prompts) > 0
    # Should show 44F, not 6.69F (using ASCII-safe format without degree symbol)
    assert "44F" in prompts[0]["prompt"]
    # Metadata should include both
    assert prompts[0]["metadata"]["temperature_celsius"] == 6.69
    assert prompts[0]["metadata"]["temperature_fahrenheit"] == 44

