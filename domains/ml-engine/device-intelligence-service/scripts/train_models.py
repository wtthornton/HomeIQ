#!/usr/bin/env python3
"""
Standalone Model Training Script for Device Intelligence Service

This script can be run independently to train ML models without starting the full service.
It can be used for:
- Scheduled model retraining
- Manual model updates
- Testing model training in isolation
- CI/CD pipeline integration

Usage:
    python scripts/train_models.py [--days-back 180] [--force] [--verbose]
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path to import service modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Settings
from src.core.database import close_database, initialize_database
from src.core.predictive_analytics import PredictiveAnalyticsEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('training.log')
    ]
)
logger = logging.getLogger(__name__)


async def train_models(
    days_back: int = 180,
    force: bool = False,
    verbose: bool = False,
    use_synthetic: bool = False,
    synthetic_count: int = 1000
):
    """
    Train ML models.
    
    Args:
        days_back: Number of days of historical data to use
        force: Force retrain even if models exist
        verbose: Enable verbose logging
        use_synthetic: Use synthetic device data for training (Epic 46.3)
        synthetic_count: Number of synthetic samples to generate (if use_synthetic=True)
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("=" * 80)
    logger.info("ML Model Training Script")
    logger.info("=" * 80)
    logger.info(f"Days back: {days_back}")
    logger.info(f"Force retrain: {force}")
    logger.info(f"Use synthetic data: {use_synthetic}")
    if use_synthetic:
        logger.info(f"Synthetic sample count: {synthetic_count}")
    logger.info("")

    try:
        # Initialize settings and database
        logger.info("📊 Initializing database connection...")
        settings = Settings()
        await initialize_database(settings)
        logger.info("✅ Database initialized")

        # Create analytics engine
        logger.info("🤖 Creating predictive analytics engine...")
        engine = PredictiveAnalyticsEngine()

        # Check if models already exist
        if engine.is_trained and not force:
            logger.info("ℹ️  Models are already trained. Use --force to retrain.")
            status = engine.get_model_status()
            logger.info(f"   Current version: {status['model_metadata'].get('version', 'unknown')}")
            logger.info(f"   Training date: {status['model_metadata'].get('training_date', 'unknown')}")
            return 0

        # Generate synthetic data if requested (Epic 46.3)
        historical_data = None
        if use_synthetic:
            logger.info("📊 Generating synthetic device data...")
            try:
                from src.training.synthetic_device_generator import SyntheticDeviceGenerator
                generator = SyntheticDeviceGenerator()
                historical_data = generator.generate_training_data(
                    count=synthetic_count,
                    days=days_back
                )
                logger.info(f"✅ Generated {len(historical_data)} synthetic device samples")
            except Exception as e:
                logger.warning(f"⚠️ Failed to generate synthetic data: {e}")
                logger.warning("   Falling back to database data")
                historical_data = None

        # Train models
        logger.info("🚀 Starting model training...")
        logger.info("")

        await engine.train_models(historical_data=historical_data, days_back=days_back)

        if engine.is_trained:
            # Get training results
            status = engine.get_model_status()
            metadata = status.get('model_metadata', {})
            performance = status.get('model_performance', {})

            logger.info("")
            logger.info("=" * 80)
            logger.info("✅ Training Complete!")
            logger.info("=" * 80)
            logger.info(f"Model Version: {metadata.get('version', 'unknown')}")
            logger.info(f"Training Date: {metadata.get('training_date', 'unknown')}")
            logger.info(f"Data Source: {metadata.get('data_source', 'unknown')}")
            logger.info(f"Training Duration: {metadata.get('training_duration_seconds', 0):.2f} seconds")
            logger.info("")
            logger.info("Training Data Stats:")
            stats = metadata.get('training_data_stats', {})
            logger.info(f"  - Sample Count: {stats.get('sample_count', 0)}")
            logger.info(f"  - Unique Devices: {stats.get('unique_devices', 0)}")
            logger.info(f"  - Days Back: {stats.get('days_back', 0)}")
            logger.info("")
            logger.info("Model Performance:")
            logger.info(f"  - Accuracy: {performance.get('accuracy', 0):.3f}")
            logger.info(f"  - Precision: {performance.get('precision', 0):.3f}")
            logger.info(f"  - Recall: {performance.get('recall', 0):.3f}")
            logger.info(f"  - F1 Score: {performance.get('f1_score', 0):.3f}")
            logger.info("")
            logger.info("=" * 80)

            return 0
        else:
            logger.error("❌ Training failed - models not trained")
            return 1

    except Exception as e:
        logger.error(f"❌ Error during training: {e}", exc_info=True)
        return 1
    finally:
        # Cleanup
        try:
            await close_database()
            logger.info("✅ Database connection closed")
        except Exception as e:
            logger.warning(f"⚠️  Error closing database: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Train ML models for Device Intelligence Service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Train with default settings (180 days)
  python scripts/train_models.py
  
  # Train with custom days back
  python scripts/train_models.py --days-back 90
  
  # Force retrain even if models exist
  python scripts/train_models.py --force
  
  # Verbose output
  python scripts/train_models.py --verbose
        """
    )

    parser.add_argument(
        '--days-back',
        type=int,
        default=180,
        help='Number of days of historical data to use for training (default: 180)'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='Force retraining even if models already exist'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--synthetic-data',
        action='store_true',
        help='Use synthetic device data for training (Epic 46.3: for initial training)'
    )
    parser.add_argument(
        '--synthetic-count',
        type=int,
        default=1000,
        help='Number of synthetic samples to generate (default: 1000, only used with --synthetic-data)'
    )

    args = parser.parse_args()

    # Run training
    exit_code = asyncio.run(train_models(
        days_back=args.days_back,
        force=args.force,
        verbose=args.verbose,
        use_synthetic=args.synthetic_data,
        synthetic_count=args.synthetic_count
    ))

    sys.exit(exit_code)


if __name__ == "__main__":
    main()

