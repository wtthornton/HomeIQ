#!/usr/bin/env python3
"""
Production Readiness Script
Builds, deploys, tests, generates data, trains models, and prepares for production.

Enhanced with Epic 42 & 43 improvements:
- Pre-flight validation of dependencies and configuration
- Critical vs optional component classification
- Enhanced error messages with actionable fix instructions
- Model quality validation with defined thresholds
- Component documentation (see docs/architecture/production-readiness-components.md)

Usage:
    python scripts/prepare_for_production.py
    python scripts/prepare_for_production.py --quick  # Smaller dataset, faster
    python scripts/prepare_for_production.py --skip-build --skip-deploy
    python scripts/prepare_for_production.py --skip-validation  # Skip pre-flight checks (advanced)
    python scripts/prepare_for_production.py --dry-run  # Test without making changes
"""
import argparse
import asyncio
import logging
import sys
from pathlib import Path

from production_readiness.runner import PipelineConfig, run_pipeline

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.debug("Loaded environment variables from .env file")
except ImportError:
    logger.debug("python-dotenv not installed - environment variables must be set manually or via system")
except Exception as e:
    logger.warning(f"Could not load .env file: {e} - continuing with system environment variables")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Prepare system for production deployment'
    )
    parser.add_argument('--skip-build', action='store_true', help='Skip Docker build step')
    parser.add_argument('--skip-deploy', action='store_true', help='Skip deployment step')
    parser.add_argument('--skip-smoke', action='store_true', help='Skip smoke tests')
    parser.add_argument('--skip-generation', action='store_true', help='Skip test data generation')
    parser.add_argument('--skip-training', action='store_true', help='Skip model training')
    parser.add_argument('--quick', action='store_true', help='Use smaller dataset (10 homes, 7 days)')
    parser.add_argument('--count', type=int, help='Number of synthetic homes to generate (default: 100, or 10 in quick mode)')
    parser.add_argument('--days', type=int, help='Number of days of events per home (default: 90, or 7 in quick mode)')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--output-dir', type=str, help='Custom output directory for reports')
    parser.add_argument('--skip-validation', action='store_true', help='Skip pre-flight dependency validation (advanced users only)')
    parser.add_argument('--allow-low-quality', action='store_true', help='Allow models that don\'t meet quality thresholds to proceed (advanced users only)')
    parser.add_argument('--force-regenerate', action='store_true', help='Force regeneration of test data even if it already exists')
    parser.add_argument('--dry-run', action='store_true', help='Run in dry-run mode (no actual changes, for testing)')
    
    return parser.parse_args()


async def main() -> int:
    """Main entry point."""
    args = parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Setup output directory
    output_dir = Path(args.output_dir) if args.output_dir else None
    
    # Create pipeline configuration
    config = PipelineConfig(
        skip_build=args.skip_build,
        skip_deploy=args.skip_deploy,
        skip_smoke=args.skip_smoke,
        skip_generation=args.skip_generation,
        skip_training=args.skip_training,
        quick=args.quick,
        count=args.count,
        days=args.days,
        skip_validation=args.skip_validation,
        allow_low_quality=args.allow_low_quality,
        force_regenerate=args.force_regenerate,
        output_dir=output_dir,
        dry_run=args.dry_run
    )
    
    # Run pipeline
    exit_code = await run_pipeline(config)
    
    if exit_code == 0:
        logger.info("✅ SYSTEM IS PRODUCTION READY")
    else:
        logger.warning("⚠️  SYSTEM IS NOT PRODUCTION READY - Review report for details")
        logger.warning("   Critical components must pass for production deployment")
    
    return exit_code


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
