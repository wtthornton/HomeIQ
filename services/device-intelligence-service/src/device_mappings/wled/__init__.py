"""
WLED Device Handler

Handler for WLED devices, including master controllers and segments.
"""

from .handler import WLEDHandler

def register(registry):
    """Register the WLED handler with the device mapping registry."""
    registry.register("wled", WLEDHandler())

