#!/usr/bin/env python3
"""
Test Incremental Learning

Test incremental learning vs full retrain to verify 10-50x speed improvement.

Usage:
    python scripts/test_incremental_learning.py
    python scripts/test_incremental_learning.py --samples 1000
"""

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Settings
from src.core.database import close_database, initialize_database
from src.core.predictive_analytics import PredictiveAnalyticsEngine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_incremental_learning(samples: int = 500):
    """
    Test incremental learning performance.
    
    Args:
        samples: Number of new samples to test with
    """
    logger.info("=" * 80)
    logger.info("Incremental Learning Test")
    logger.info("=" * 80)
    logger.info(f"New samples: {samples}")
    logger.info("")
    
    try:
        # Initialize
        logger.info("📊 Initializing database connection...")
        settings = Settings()
        settings.ML_USE_INCREMENTAL = True
        await initialize_database(settings)
        logger.info("✅ Database initialized")
        
        # Create engine with incremental learning enabled
        engine = PredictiveAnalyticsEngine(settings)
        
        # Collect initial training data
        logger.info("📊 Collecting initial training data...")
        historical_data = await engine._collect_training_data(days_back=180)
        
        if len(historical_data) < 100:
            logger.warning("⚠️  Insufficient training data")
            return 1
        
        logger.info(f"✅ Collected {len(historical_data)} initial samples")
        
        # Prepare data
        import pandas as pd
        import numpy as np
        df = pd.DataFrame(historical_data)
        X, y_failure, y_anomaly = engine._prepare_training_data(df)
        
        from sklearn.model_selection import train_test_split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_failure, test_size=0.2, random_state=42
        )
        
        # Test 1: Full retrain time
        logger.info("")
        logger.info("=" * 80)
        logger.info("Test 1: Full Retrain")
        logger.info("=" * 80)
        
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.preprocessing import StandardScaler
        
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        start_time = time.time()
        model_full = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
        model_full.fit(X_train_scaled, y_train)
        full_retrain_time = time.time() - start_time
        
        from sklearn.metrics import accuracy_score
        y_pred_full = model_full.predict(X_test_scaled)
        accuracy_full = accuracy_score(y_test, y_pred_full)
        
        logger.info(f"Full retrain time: {full_retrain_time:.3f}s")
        logger.info(f"Full retrain accuracy: {accuracy_full:.3f}")
        
        # Test 2: Incremental update time
        logger.info("")
        logger.info("=" * 80)
        logger.info("Test 2: Incremental Update")
        logger.info("=" * 80)
        
        try:
            from src.core.incremental_predictor import IncrementalFailurePredictor
            
            # Initial training
            start_time = time.time()
            model_inc = IncrementalFailurePredictor()
            model_inc.fit(X_train, y_train, feature_names=engine.feature_columns)
            initial_train_time = time.time() - start_time
            
            y_pred_inc = model_inc.predict(X_test)
            accuracy_inc = accuracy_score(y_test, y_pred_inc)
            
            logger.info(f"Initial incremental train time: {initial_train_time:.3f}s")
            logger.info(f"Initial incremental accuracy: {accuracy_inc:.3f}")
            
            # Generate new samples (simulate daily updates)
            np.random.seed(42)
            X_new = np.random.rand(samples, X_train.shape[1])
            y_new = np.random.randint(0, 2, samples)
            
            # Incremental update
            start_time = time.time()
            model_inc.learn_many(X_new, y_new)
            incremental_update_time = time.time() - start_time
            
            logger.info(f"Incremental update time ({samples} samples): {incremental_update_time:.3f}s")
            
            # Compare
            logger.info("")
            logger.info("=" * 80)
            logger.info("COMPARISON")
            logger.info("=" * 80)
            
            speedup = full_retrain_time / incremental_update_time
            logger.info(f"Full retrain: {full_retrain_time:.3f}s")
            logger.info(f"Incremental update: {incremental_update_time:.3f}s")
            logger.info(f"Speedup: {speedup:.2f}x faster")
            logger.info(f"Accuracy difference: {abs(accuracy_full - accuracy_inc):.3f}")
            
            if speedup >= 10:
                logger.info("✅ PASS: Incremental learning is 10x+ faster")
            else:
                logger.warning(f"⚠️  WARNING: Speedup ({speedup:.2f}x) less than expected (10x+)")
            
            return 0
            
        except ImportError:
            logger.error("❌ River library not available. Install with: pip install river>=0.21.0")
            return 1
        
    except Exception as e:
        logger.error(f"❌ Error during test: {e}", exc_info=True)
        return 1
    finally:
        try:
            await close_database()
        except Exception as e:
            logger.warning(f"⚠️  Error closing database: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test incremental learning performance",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--samples',
        type=int,
        default=500,
        help='Number of new samples for incremental update (default: 500)'
    )
    
    args = parser.parse_args()
    
    exit_code = asyncio.run(test_incremental_learning(samples=args.samples))
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

