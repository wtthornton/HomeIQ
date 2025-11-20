"""
Device Intelligence Module - Epic-AI-2

This module provides universal device capability discovery and feature-based
suggestion generation for Home Assistant devices.

Components:
- CapabilityParser: Universal parser for Zigbee2MQTT 'exposes' format (Story AI2.1)
- MQTTCapabilityListener: Subscribes to Zigbee2MQTT bridge for capability discovery (Story AI2.1)
- FeatureAnalyzer: Analyzes device utilization (Story AI2.3)
- FeatureSuggestionGenerator: Generates LLM-powered suggestions (Story 2.4)

Stories:
- AI2.1: MQTT Capability Listener & Universal Parser
- AI2.2: Capability Database Schema & Storage
- AI2.3: Device Matching & Feature Analysis
"""

from .capability_batch import update_device_capabilities_batch
from .capability_parser import CapabilityParser
from .feature_analyzer import FeatureAnalyzer
from .feature_suggestion_generator import FeatureSuggestionGenerator
from .mqtt_capability_listener import MQTTCapabilityListener

__all__ = [
    "CapabilityParser",
    "MQTTCapabilityListener",
    "FeatureAnalyzer",
    "FeatureSuggestionGenerator",
    "update_device_capabilities_batch",
]

