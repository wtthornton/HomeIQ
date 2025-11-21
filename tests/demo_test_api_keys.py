#!/usr/bin/env python3
"""
Demo script showing how to test API keys with real credentials

This script demonstrates how to use the API key validation tests
with actual API keys and tokens.

Usage:
    python tests/demo_test_api_keys.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio

from tests.test_api_keys import APITestSuite


async def demo_with_real_credentials():
    """Demo function showing how to test with real credentials"""

    print("=" * 80)
    print("API KEY VALIDATION DEMO")
    print("=" * 80)

    print("\nThis demo shows how to test your API keys with real credentials.")
    print("\nTo test with real credentials, you have several options:")

    print("\n1. SET ENVIRONMENT VARIABLES:")
    print("   export HOME_ASSISTANT_URL='http://your-ha-instance:8123'")
    print("   export HOME_ASSISTANT_TOKEN='your_real_long_lived_token'")
    print("   export WEATHER_API_KEY='your_real_openweathermap_key'")

    print("\n2. USE COMMAND LINE OVERRIDES:")
    print("   python tests/test_api_keys.py \\")
    print("     --ha-url http://your-ha-instance:8123 \\")
    print("     --ha-token your_real_token \\")
    print("     --weather-key your_real_key")

    print("\n3. UPDATE YOUR .env FILE:")
    print("   HOME_ASSISTANT_URL=http://your-ha-instance:8123")
    print("   HOME_ASSISTANT_TOKEN=your_real_long_lived_token")
    print("   WEATHER_API_KEY=your_real_openweathermap_key")

    print("\n4. CREATE A PRODUCTION ENV FILE:")
    print("   cp infrastructure/env.example .env.production")
    print("   # Edit .env.production with real values")
    print("   python tests/test_api_keys.py --env-file .env.production")

    print("\n" + "=" * 80)
    print("CURRENT TEST RESULTS (WITH PLACEHOLDER VALUES)")
    print("=" * 80)

    # Run the test suite with current environment
    test_suite = APITestSuite()
    summary = await test_suite.run_all_tests()
    test_suite.print_summary(summary)

    print("\n" + "=" * 80)
    print("INTERPRETATION OF RESULTS")
    print("=" * 80)

    print("\n[PASS] Environment Variables:")
    print("  [✓] All required environment variables are present")
    print("  [✓] Configuration is properly loaded")

    print("\n[FAIL] Home Assistant API Tests:")
    print("  [✗] Expected failure - using placeholder token 'your_long_lived_access_token_here'")
    print("  [✗] Replace with real Home Assistant long-lived access token")

    print("\n[FAIL] Weather API Tests:")
    print("  [✗] Expected failure - using placeholder API key 'your_openweathermap_api_key_here'")
    print("  [✗] Replace with real OpenWeatherMap API key")

    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)

    print("\n1. Get a Home Assistant Long-Lived Access Token:")
    print("   - Go to Home Assistant > Profile > Long-lived access tokens")
    print("   - Click 'Create Token'")
    print("   - Copy the generated token")

    print("\n2. Get an OpenWeatherMap API Key:")
    print("   - Go to https://openweathermap.org/api")
    print("   - Sign up for a free account")
    print("   - Copy your API key from the dashboard")

    print("\n3. Test with Real Credentials:")
    print("   python tests/test_api_keys.py \\")
    print("     --ha-url http://your-ha-instance:8123 \\")
    print("     --ha-token YOUR_REAL_HA_TOKEN \\")
    print("     --weather-key YOUR_REAL_WEATHER_KEY")

    print("\n4. Expected Results with Real Credentials:")
    print("   [✓] Environment Variables: PASS")
    print("   [✓] Home Assistant Connection: PASS")
    print("   [✓] Home Assistant WebSocket: PASS")
    print("   [✓] Home Assistant Permissions: PASS")
    print("   [✓] Weather API Key Validation: PASS")
    print("   [✓] Weather API Quota Test: PASS")


if __name__ == "__main__":
    asyncio.run(demo_with_real_credentials())
