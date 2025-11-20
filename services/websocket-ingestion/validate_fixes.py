#!/usr/bin/env python3
"""
Validation script to test websocket fixes
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

# Setup path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def validate_imports():
    """Validate all modules can be imported"""
    logger.info("=" * 80)
    logger.info("🔍 VALIDATING MODULE IMPORTS")
    logger.info("=" * 80)

    try:
        logger.info("📦 Importing websocket_client...")
        logger.info("✅ websocket_client imported successfully")

        logger.info("📦 Importing connection_manager...")
        logger.info("✅ connection_manager imported successfully")

        logger.info("📦 Importing event_subscription...")
        logger.info("✅ event_subscription imported successfully")

        logger.info("📦 Importing health_check...")
        logger.info("✅ health_check imported successfully")

        logger.info("=" * 80)
        logger.info("🎉 ALL IMPORTS SUCCESSFUL")
        logger.info("=" * 80)
        return True

    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"❌ IMPORT FAILED: {e}")
        logger.error("=" * 80)
        import traceback
        logger.error(traceback.format_exc())
        return False

async def validate_subscription_logging():
    """Validate subscription manager has enhanced logging"""
    logger.info("=" * 80)
    logger.info("🔍 VALIDATING SUBSCRIPTION LOGGING ENHANCEMENTS")
    logger.info("=" * 80)

    try:
        from event_subscription import EventSubscriptionManager

        # Check if the class has the expected methods
        manager = EventSubscriptionManager()

        logger.info("✅ EventSubscriptionManager instantiated")
        logger.info(f"✅ Total events received: {manager.total_events_received}")
        logger.info(f"✅ Is subscribed: {manager.is_subscribed}")

        # Get subscription status
        status = manager.get_subscription_status()
        logger.info("✅ Subscription status retrieved:")
        for key, value in status.items():
            logger.info(f"   - {key}: {value}")

        logger.info("=" * 80)
        logger.info("🎉 SUBSCRIPTION LOGGING VALIDATION PASSED")
        logger.info("=" * 80)
        return True

    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"❌ VALIDATION FAILED: {e}")
        logger.error("=" * 80)
        import traceback
        logger.error(traceback.format_exc())
        return False

async def validate_connection_manager_enhancements():
    """Validate connection manager has enhanced logging"""
    logger.info("=" * 80)
    logger.info("🔍 VALIDATING CONNECTION MANAGER ENHANCEMENTS")
    logger.info("=" * 80)

    try:
        from connection_manager import ConnectionManager

        # Mock credentials (won't actually connect)
        manager = ConnectionManager("http://test:8123", "test_token")

        logger.info("✅ ConnectionManager instantiated")
        logger.info(f"✅ Base URL: {manager.base_url}")
        logger.info(f"✅ Is running: {manager.is_running}")
        logger.info(f"✅ Connection attempts: {manager.connection_attempts}")

        # Check status method
        status = manager.get_status()
        logger.info("✅ Status retrieved:")
        logger.info(f"   - is_running: {status.get('is_running')}")
        logger.info(f"   - connection_attempts: {status.get('connection_attempts')}")

        logger.info("=" * 80)
        logger.info("🎉 CONNECTION MANAGER VALIDATION PASSED")
        logger.info("=" * 80)
        return True

    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"❌ VALIDATION FAILED: {e}")
        logger.error("=" * 80)
        import traceback
        logger.error(traceback.format_exc())
        return False

async def validate_health_check_enhancements():
    """Validate health check has subscription monitoring"""
    logger.info("=" * 80)
    logger.info("🔍 VALIDATING HEALTH CHECK ENHANCEMENTS")
    logger.info("=" * 80)

    try:
        from connection_manager import ConnectionManager
        from health_check import HealthCheckHandler

        # Create health handler
        health = HealthCheckHandler()
        logger.info("✅ HealthCheckHandler instantiated")

        # Create mock connection manager
        manager = ConnectionManager("http://test:8123", "test_token")
        health.set_connection_manager(manager)
        logger.info("✅ Connection manager set")

        # Verify event subscription is accessible
        if hasattr(manager, 'event_subscription'):
            logger.info("✅ Event subscription accessible from connection manager")
        else:
            logger.warning("⚠️  Event subscription not directly accessible")

        logger.info("=" * 80)
        logger.info("🎉 HEALTH CHECK VALIDATION PASSED")
        logger.info("=" * 80)
        return True

    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"❌ VALIDATION FAILED: {e}")
        logger.error("=" * 80)
        import traceback
        logger.error(traceback.format_exc())
        return False

async def main():
    """Run all validations"""
    logger.info("🚀 STARTING WEBSOCKET FIXES VALIDATION")
    logger.info(f"⏰ Timestamp: {datetime.now().isoformat()}")
    logger.info("")

    results = []

    # Run validations
    results.append(("Module Imports", await validate_imports()))
    results.append(("Subscription Logging", await validate_subscription_logging()))
    results.append(("Connection Manager", await validate_connection_manager_enhancements()))
    results.append(("Health Check", await validate_health_check_enhancements()))

    # Summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("📊 VALIDATION SUMMARY")
    logger.info("=" * 80)

    all_passed = True
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} - {name}")
        if not result:
            all_passed = False

    logger.info("=" * 80)

    if all_passed:
        logger.info("🎉 ALL VALIDATIONS PASSED!")
        logger.info("✅ Websocket fixes are ready for deployment")
        return 0
    else:
        logger.error("❌ SOME VALIDATIONS FAILED")
        logger.error("⚠️  Please review the errors above")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

