"""
Hue Device Handler

Handler for Philips Hue devices, including Room/Zone groups and individual lights.
"""

from .handler import HueHandler

def register(registry):
    """Register the Hue handler with the device mapping registry."""
    registry.register("hue", HueHandler())

