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

import sys
import os
import argparse
import asyncio
import logging
from pathlib import Path

# Add parent directory to path to import service modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.predictive_analytics import PredictiveAnalyticsEngine
from src.core.database import initialize_database, close_database
from src.config import Settings

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


async def train_models(days_back: int = 180, force: bool = False, verbose: bool = False):
    """Train ML models."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("=" * 80)
    logger.info("ML Model Training Script")
    logger.info("=" * 80)
    logger.info(f"Days back: {days_back}")
    logger.info(f"Force retrain: {force}")
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
        
        # Train models
        logger.info("🚀 Starting model training...")
        logger.info("")
        
        await engine.train_models(days_back=days_back)
        
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
    
    args = parser.parse_args()
    
    # Run training
    exit_code = asyncio.run(train_models(
        days_back=args.days_back,
        force=args.force,
        verbose=args.verbose
    ))
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

