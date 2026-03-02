"""
Tests for filters.py — EventFilter pure functions
"""

import pandas as pd
from src.pattern_analyzer.filters import (
    EventFilter,
)


class TestGetDomain:
    """Test EventFilter.get_domain static method."""

    def test_extracts_light_domain(self):
        assert EventFilter.get_domain("light.bedroom") == "light"

    def test_extracts_sensor_domain(self):
        assert EventFilter.get_domain("sensor.temperature") == "sensor"

    def test_extracts_binary_sensor_domain(self):
        assert EventFilter.get_domain("binary_sensor.motion") == "binary_sensor"

    def test_returns_empty_for_no_dot(self):
        assert EventFilter.get_domain("nodotshere") == ""

    def test_handles_multiple_dots(self):
        assert EventFilter.get_domain("sensor.something.extra") == "sensor"


class TestIsExternalDataEntity:
    """Test EventFilter.is_external_data_entity static method."""

    def test_weather_domain_is_external(self):
        assert EventFilter.is_external_data_entity("weather.home") is True

    def test_calendar_domain_is_external(self):
        assert EventFilter.is_external_data_entity("calendar.work") is True

    def test_sports_tracker_is_external(self):
        assert EventFilter.is_external_data_entity("sensor.nfl_team_tracker") is True

    def test_carbon_intensity_is_external(self):
        assert EventFilter.is_external_data_entity("sensor.carbon_intensity_uk") is True

    def test_light_is_not_external(self):
        assert EventFilter.is_external_data_entity("light.bedroom") is False

    def test_switch_is_not_external(self):
        assert EventFilter.is_external_data_entity("switch.kitchen") is False


class TestIsSystemNoise:
    """Test EventFilter.is_system_noise static method."""

    def test_image_domain_is_noise(self):
        assert EventFilter.is_system_noise("image.roborock_map") is True

    def test_event_domain_is_noise(self):
        assert EventFilter.is_system_noise("event.button_pressed") is True

    def test_update_domain_is_noise(self):
        assert EventFilter.is_system_noise("update.core") is True

    def test_system_sensor_prefix_is_noise(self):
        assert EventFilter.is_system_noise("sensor.home_assistant_uptime") is True

    def test_cpu_pattern_is_noise(self):
        assert EventFilter.is_system_noise("sensor.processor_cpu_total") is True

    def test_battery_pattern_is_noise(self):
        assert EventFilter.is_system_noise("sensor.phone_battery") is True

    def test_light_is_not_noise(self):
        assert EventFilter.is_system_noise("light.bedroom") is False

    def test_motion_sensor_is_not_noise(self):
        assert EventFilter.is_system_noise("binary_sensor.hallway_motion") is False


class TestIsActionableEntity:
    """Test EventFilter.is_actionable_entity static method."""

    def test_light_is_actionable(self):
        assert EventFilter.is_actionable_entity("light.bedroom") is True

    def test_switch_is_actionable(self):
        assert EventFilter.is_actionable_entity("switch.kitchen") is True

    def test_motion_sensor_is_actionable(self):
        assert EventFilter.is_actionable_entity("binary_sensor.hallway_motion") is True

    def test_weather_is_not_actionable(self):
        assert EventFilter.is_actionable_entity("weather.home") is False

    def test_system_sensor_is_not_actionable(self):
        assert EventFilter.is_actionable_entity("sensor.home_assistant_uptime") is False

    def test_sports_tracker_is_not_actionable(self):
        assert EventFilter.is_actionable_entity("sensor.nfl_team_tracker") is False


class TestFilterEvents:
    """Test EventFilter.filter_events static method."""

    def test_filters_external_and_noise(self):
        df = pd.DataFrame({
            "entity_id": [
                "light.bedroom",
                "weather.home",
                "sensor.home_assistant_uptime",
                "switch.kitchen",
            ]
        })

        result = EventFilter.filter_events(df)

        assert len(result) == 2
        assert "light.bedroom" in result["entity_id"].values
        assert "switch.kitchen" in result["entity_id"].values

    def test_empty_df_returns_empty(self):
        df = pd.DataFrame(columns=["entity_id"])
        result = EventFilter.filter_events(df)
        assert result.empty

    def test_missing_column_returns_original(self):
        df = pd.DataFrame({"other_col": ["a", "b"]})
        result = EventFilter.filter_events(df)
        assert len(result) == 2

    def test_custom_entity_column(self):
        df = pd.DataFrame({
            "eid": ["light.bedroom", "weather.home"]
        })
        result = EventFilter.filter_events(df, entity_column="eid")
        assert len(result) == 1
        assert result.iloc[0]["eid"] == "light.bedroom"

    def test_all_noise_returns_empty(self):
        df = pd.DataFrame({
            "entity_id": ["weather.home", "image.map", "event.click"]
        })
        result = EventFilter.filter_events(df)
        assert len(result) == 0
