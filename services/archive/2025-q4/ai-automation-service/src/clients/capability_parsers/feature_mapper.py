"""
Feature Mapper - Maps bitmask features to friendly descriptions.

Provides human-readable descriptions for Home Assistant entity capabilities.
"""


# Mapping of feature names to friendly descriptions
FEATURE_DESCRIPTIONS: dict[str, dict[str, str]] = {
    'light': {
        'brightness': 'Adjust brightness (0-100%)',
        'color_temp': 'Set color temperature (warm to cool)',
        'rgb_color': 'Change color (RGB)',
        'white_value': 'Adjust white level',
        'flash': 'Flash on/off',
        'transition': 'Smooth transitions (fade in/out)',
        'effect': 'Light effects',
    },
    'climate': {
        'temperature': 'Set target temperature',
        'hvac_mode': 'Change heating/cooling mode',
        'current_temperature': 'Monitor current temperature',
        'humidity': 'Control humidity levels',
        'target_humidity': 'Set target humidity',
        'fan_mode': 'Adjust fan speed',
        'swing_mode': 'Control air swing',
        'preset': 'Use preset modes',
        'aux_heat': 'Enable auxiliary heating',
    },
    'cover': {
        'open': 'Open cover',
        'close': 'Close cover',
        'position': 'Set position (0-100%)',
        'tilt': 'Adjust tilt angle',
        'stop': 'Stop movement',
    },
    'fan': {
        'on_off': 'Turn on/off',
        'speed': 'Adjust speed level',
        'direction': 'Reverse direction',
        'oscillate': 'Enable oscillation',
        'preset': 'Use preset modes',
    },
    'switch': {
        'on_off': 'Turn on/off',
        'current_power': 'Monitor power usage',
    },
    'sensor': {
        'read': 'Read sensor value',
    },
    'binary_sensor': {
        'read': 'Read sensor state',
    },
    'camera': {
        'stream': 'Live video stream',
        'snapshot': 'Take snapshot',
    },
    'lock': {
        'lock': 'Lock door',
        'unlock': 'Unlock door',
        'open': 'Open door',
    },
    'media_player': {
        'play': 'Play media',
        'pause': 'Pause playback',
        'stop': 'Stop playback',
        'volume': 'Adjust volume',
        'source': 'Change input source',
        'shuffle': 'Enable shuffle',
    },
    'vacuum': {
        'start': 'Start cleaning',
        'pause': 'Pause cleaning',
        'stop': 'Stop cleaning',
        'return_home': 'Return to dock',
        'locate': 'Locate device',
        'clean_spot': 'Spot cleaning',
    },
    'update': {
        'install': 'Install update',
        'skip': 'Skip update',
    },
}


def get_feature_description(domain: str, feature: str) -> str:
    """Get friendly description for a feature."""
    return FEATURE_DESCRIPTIONS.get(domain, {}).get(
        feature,
        f"Control {feature.replace('_', ' ')}"
    )


def generate_friendly_capabilities(domain: str, features: dict[str, bool]) -> list[str]:
    """Generate list of friendly capability descriptions."""
    friendly_caps = []
    for feature, enabled in features.items():
        if enabled:
            friendly_caps.append(get_feature_description(domain, feature))
    return friendly_caps

