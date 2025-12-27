#!/usr/bin/env python3
"""
Test script to check health handler configuration
"""
import sys

# Add the websocket-ingestion src directory to path
sys.path.append('/app/src')

from health_check import HealthCheckHandler

def test_health_handler():
    """Test health handler configuration"""
    print("Testing Health Handler Configuration...")
    
    # Create health handler
    handler = HealthCheckHandler()
    
    print(f"Health handler has websocket_service: {hasattr(handler, 'websocket_service')}")
    
    # Try to access weather enrichment stats
    if hasattr(handler, 'websocket_service'):
        print(f"WebSocket service present: {handler.websocket_service is not None}")
        if handler.websocket_service and hasattr(handler.websocket_service, 'weather_enrichment'):
            print(f"Weather enrichment service present: {handler.websocket_service.weather_enrichment is not None}")
        else:
            print("Weather enrichment service not present")
    else:
        print("WebSocket service reference not set")

if __name__ == "__main__":
    test_health_handler()
