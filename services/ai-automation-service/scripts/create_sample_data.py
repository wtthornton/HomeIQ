#!/usr/bin/env python3
"""
Create Sample HA Data for Testing
Generates realistic Home Assistant events for preprocessing pipeline testing
"""

import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd


def create_sample_ha_events(num_events: int = 1000, days_back: int = 30) -> pd.DataFrame:
    """
    Create realistic sample HA events
    
    Args:
        num_events: Number of events to generate
        days_back: How many days back to start from
    
    Returns:
        DataFrame with HA event structure
    """

    # Device definitions
    devices = {
        'light.living_room': {'type': 'light', 'area': 'living_room', 'name': 'Living Room Light'},
        'light.kitchen': {'type': 'light', 'area': 'kitchen', 'name': 'Kitchen Light'},
        'light.bedroom': {'type': 'light', 'area': 'bedroom', 'name': 'Bedroom Light'},
        'switch.coffee_maker': {'type': 'switch', 'area': 'kitchen', 'name': 'Coffee Maker'},
        'switch.tv': {'type': 'switch', 'area': 'living_room', 'name': 'TV'},
        'sensor.motion_living': {'type': 'sensor', 'area': 'living_room', 'name': 'Motion Sensor'},
        'sensor.motion_kitchen': {'type': 'sensor', 'area': 'kitchen', 'name': 'Motion Sensor'},
        'climate.thermostat': {'type': 'climate', 'area': 'living_room', 'name': 'Thermostat'},
        'lock.front_door': {'type': 'lock', 'area': 'entrance', 'name': 'Front Door Lock'},
        'camera.front_door': {'type': 'camera', 'area': 'entrance', 'name': 'Front Door Camera'},
    }

    # Time patterns (realistic HA usage)
    time_patterns = {
        'morning': {
            'hours': [6, 7, 8, 9],
            'devices': ['light.bedroom', 'light.kitchen', 'switch.coffee_maker', 'sensor.motion_kitchen'],
            'states': ['on', 'off']
        },
        'day': {
            'hours': [10, 11, 12, 13, 14, 15, 16],
            'devices': ['light.living_room', 'switch.tv', 'sensor.motion_living', 'climate.thermostat'],
            'states': ['on', 'off', 'auto']
        },
        'evening': {
            'hours': [17, 18, 19, 20, 21],
            'devices': ['light.living_room', 'light.kitchen', 'switch.tv', 'climate.thermostat'],
            'states': ['on', 'off']
        },
        'night': {
            'hours': [22, 23, 0, 1, 2, 3, 4, 5],
            'devices': ['light.bedroom', 'lock.front_door', 'camera.front_door'],
            'states': ['on', 'off', 'locked', 'unlocked']
        }
    }

    events = []
    start_time = datetime.now() - timedelta(days=days_back)

    for i in range(num_events):
        # Random time within the period
        event_time = start_time + timedelta(
            days=random.randint(0, days_back-1),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59)
        )

        # Determine time pattern
        hour = event_time.hour
        if 6 <= hour < 12:
            pattern = 'morning'
        elif 12 <= hour < 17:
            pattern = 'day'
        elif 17 <= hour < 22:
            pattern = 'evening'
        else:
            pattern = 'night'

        # Select device from pattern
        device_id = random.choice(time_patterns[pattern]['devices'])
        device_info = devices[device_id]

        # Generate state change
        old_state = random.choice(['on', 'off', 'unknown'])
        new_state = random.choice(time_patterns[pattern]['states'])

        # Skip if same state
        if old_state == new_state:
            continue

        # Create event
        event = {
            'event_id': f'evt_{i:06d}',
            'timestamp': event_time,
            'device_id': device_id,
            'entity_id': device_id,
            'device_name': device_info['name'],
            'device_type': device_info['type'],
            'area': device_info['area'],
            'old_state': old_state,
            'new_state': new_state,
            'attributes': {
                'friendly_name': device_info['name'],
                'unit_of_measurement': 'W' if 'sensor' in device_id else None,
                'brightness': random.randint(0, 255) if 'light' in device_id else None,
                'temperature': random.uniform(18, 25) if 'climate' in device_id else None,
            }
        }

        events.append(event)

    return pd.DataFrame(events)

def create_sample_weather_data(days_back: int = 30) -> pd.DataFrame:
    """Create sample weather data for contextual features"""

    weather_conditions = ['sunny', 'cloudy', 'rainy', 'snowy', 'foggy']
    temperatures = np.random.normal(20, 10, days_back * 24)  # 20°C ± 10°C

    weather_data = []
    start_time = datetime.now() - timedelta(days=days_back)

    for day in range(days_back):
        for hour in range(24):
            timestamp = start_time + timedelta(days=day, hours=hour)

            # Sun elevation (simplified)
            sun_elevation = max(0, 90 * np.sin(np.pi * (hour - 6) / 12)) if 6 <= hour <= 18 else 0

            weather_data.append({
                'timestamp': timestamp,
                'temperature': temperatures[day * 24 + hour],
                'weather_condition': random.choice(weather_conditions),
                'sun_elevation': sun_elevation,
                'is_sunrise': hour == 7,  # Simplified sunrise
                'is_sunset': hour == 19,  # Simplified sunset
            })

    return pd.DataFrame(weather_data)

def create_sample_occupancy_data(days_back: int = 30) -> pd.DataFrame:
    """Create sample occupancy data"""

    occupancy_data = []
    start_time = datetime.now() - timedelta(days=days_back)

    for day in range(days_back):
        # Typical home/away pattern
        home_hours = list(range(7, 9)) + list(range(17, 23))  # Morning and evening
        away_hours = list(range(9, 17))  # Work hours

        for hour in range(24):
            timestamp = start_time + timedelta(days=day, hours=hour)

            if hour in home_hours:
                occupancy = 'home'
            elif hour in away_hours:
                occupancy = 'away'
            else:
                occupancy = 'sleeping' if hour < 7 or hour >= 23 else 'home'

            occupancy_data.append({
                'timestamp': timestamp,
                'occupancy_state': occupancy
            })

    return pd.DataFrame(occupancy_data)

def main():
    """Generate all sample data files"""

    print("Creating sample HA data...")

    # Create sample events
    events_df = create_sample_ha_events(num_events=2000, days_back=30)
    print(f"Generated {len(events_df)} events")

    # Create sample weather data
    weather_df = create_sample_weather_data(days_back=30)
    print(f"Generated {len(weather_df)} weather records")

    # Create sample occupancy data
    occupancy_df = create_sample_occupancy_data(days_back=30)
    print(f"Generated {len(occupancy_df)} occupancy records")

    # Save to files
    output_dir = Path("sample_data")
    output_dir.mkdir(exist_ok=True)

    events_df.to_csv(output_dir / "ha_events.csv", index=False)
    weather_df.to_csv(output_dir / "weather_data.csv", index=False)
    occupancy_df.to_csv(output_dir / "occupancy_data.csv", index=False)

    print(f"\nSample data saved to {output_dir}/")
    print(f"- ha_events.csv: {len(events_df)} events")
    print(f"- weather_data.csv: {len(weather_df)} weather records")
    print(f"- occupancy_data.csv: {len(occupancy_df)} occupancy records")

    # Show sample
    print("\nSample events:")
    print(events_df.head())

    print("\nSample weather:")
    print(weather_df.head())

    print("\nSample occupancy:")
    print(occupancy_df.head())

if __name__ == "__main__":
    main()
