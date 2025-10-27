"""
Capability Parsers Module

Parses Home Assistant entity capabilities using the supported_features bitmask.
Eliminates hardcoded elif chains by using HA's official constants.
"""

from .bitmask_parser import BitmaskCapabilityParser

__all__ = ["BitmaskCapabilityParser"]

