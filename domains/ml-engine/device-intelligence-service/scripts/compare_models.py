#!/usr/bin/env python3
"""
Model Comparison Script

Compare RandomForest, LightGBM, and TabPFN models on the same dataset.
Measures: accuracy, precision, recall, F1, training time.

Usage:
    python scripts/compare_models.py
    python scripts/compare_models.py --days-back 90
    python scripts/compare_models.py --output results.json
"""

import argparse
import asyncio
import json
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


async def compare_models(days_back: int = 180, output_file: str | None = None):
    """
    Compare different ML models on the same dataset.
    
    Args:
        days_back: Number of days of historical data to use
        output_file: Optional JSON file to save results
    """
    logger.info("=" * 80)
    logger.info("ML Model Comparison Script")
    logger.info("=" * 80)
    logger.info(f"Days back: {days_back}")
    logger.info("")
    
    try:
        # Initialize database
        logger.info("📊 Initializing database connection...")
        settings = Settings()
        await initialize_database(settings)
        logger.info("✅ Database initialized")
        
        # Collect training data once
        logger.info(f"📊 Collecting training data from last {days_back} days...")
        engine = PredictiveAnalyticsEngine(settings)
        historical_data = await engine._collect_training_data(days_back=days_back)
        
        if len(historical_data) < 100:
            logger.warning("⚠️  Insufficient training data for comparison")
            return 1
        
        logger.info(f"✅ Collected {len(historical_data)} training samples")
        logger.info("")
        
        # Prepare data once
        import pandas as pd
        df = pd.DataFrame(historical_data)
        X, y_failure, y_anomaly = engine._prepare_training_data(df)
        
        from sklearn.model_selection import train_test_split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_failure, test_size=0.2, random_state=42
        )
        
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        results = {}
        models_to_test = ["randomforest", "lightgbm", "tabpfn"]
        
        for model_type in models_to_test:
            logger.info("")
            logger.info("=" * 80)
            logger.info(f"Testing {model_type.upper()}")
            logger.info("=" * 80)
            
            # Create new engine with model type
            test_settings = Settings()
            test_settings.ML_FAILURE_MODEL = model_type
            test_engine = PredictiveAnalyticsEngine(test_settings)
            test_engine.scalers["failure_prediction"] = scaler
            
            # Measure training time
            start_time = time.time()
            
            try:
                # Train model
                if model_type == "tabpfn":
                    from src.core.tabpfn_predictor import TabPFNFailurePredictor
                    test_engine.models["failure_prediction"] = TabPFNFailurePredictor()
                    test_engine.models["failure_prediction"].fit(
                        X_train, y_train, feature_names=test_engine.feature_columns
                    )
                    # Evaluate on unscaled features
                    await test_engine._evaluate_models(X_test, y_test, use_scaled=False)
                elif model_type == "lightgbm":
                    try:
                        from lightgbm import LGBMClassifier
                        test_engine.models["failure_prediction"] = LGBMClassifier(
                            n_estimators=100,
                            max_depth=10,
                            random_state=42,
                            class_weight="balanced",
                            device="cpu",
                            verbose=-1
                        )
                        test_engine.models["failure_prediction"].fit(X_train_scaled, y_train)
                        await test_engine._evaluate_models(X_test_scaled, y_test, use_scaled=True)
                    except ImportError:
                        logger.warning("⚠️  LightGBM not available, skipping")
                        continue
                else:  # randomforest
                    from sklearn.ensemble import RandomForestClassifier
                    test_engine.models["failure_prediction"] = RandomForestClassifier(
                        n_estimators=100,
                        max_depth=10,
                        random_state=42,
                        class_weight="balanced"
                    )
                    test_engine.models["failure_prediction"].fit(X_train_scaled, y_train)
                    await test_engine._evaluate_models(X_test_scaled, y_test, use_scaled=True)
                
                training_time = time.time() - start_time
                
                # Get performance metrics
                performance = test_engine.model_performance
                
                results[model_type] = {
                    "training_time_seconds": round(training_time, 3),
                    "accuracy": performance.get("accuracy", 0),
                    "precision": performance.get("precision", 0),
                    "recall": performance.get("recall", 0),
                    "f1_score": performance.get("f1_score", 0),
                    "status": "success"
                }
                
                logger.info(f"✅ {model_type.upper()} Results:")
                logger.info(f"   Training Time: {training_time:.3f}s")
                logger.info(f"   Accuracy: {performance.get('accuracy', 0):.3f}")
                logger.info(f"   Precision: {performance.get('precision', 0):.3f}")
                logger.info(f"   Recall: {performance.get('recall', 0):.3f}")
                logger.info(f"   F1 Score: {performance.get('f1_score', 0):.3f}")
                
            except Exception as e:
                logger.error(f"❌ Error testing {model_type}: {e}", exc_info=True)
                results[model_type] = {
                    "status": "error",
                    "error": str(e)
                }
        
        # Summary comparison
        logger.info("")
        logger.info("=" * 80)
        logger.info("COMPARISON SUMMARY")
        logger.info("=" * 80)
        
        if "randomforest" in results and results["randomforest"]["status"] == "success":
            baseline_time = results["randomforest"]["training_time_seconds"]
            baseline_acc = results["randomforest"]["accuracy"]
            
            for model_type, result in results.items():
                if result["status"] == "success" and model_type != "randomforest":
                    speedup = baseline_time / result["training_time_seconds"]
                    acc_diff = result["accuracy"] - baseline_acc
                    logger.info(f"{model_type.upper()}:")
                    logger.info(f"   Speed: {speedup:.2f}x {'faster' if speedup > 1 else 'slower'}")
                    logger.info(f"   Accuracy: {acc_diff:+.3f} ({'+' if acc_diff > 0 else ''}{acc_diff/baseline_acc*100:.1f}%)")
        
        # Save results if requested
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"✅ Results saved to {output_file}")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error during comparison: {e}", exc_info=True)
        return 1
    finally:
        try:
            await close_database()
        except Exception as e:
            logger.warning(f"⚠️  Error closing database: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Compare ML models for failure prediction",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--days-back',
        type=int,
        default=180,
        help='Number of days of historical data (default: 180)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output JSON file for results'
    )
    
    args = parser.parse_args()
    
    exit_code = asyncio.run(compare_models(
        days_back=args.days_back,
        output_file=args.output
    ))
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

