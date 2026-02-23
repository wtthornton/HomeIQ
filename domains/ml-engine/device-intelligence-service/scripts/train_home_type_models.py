#!/usr/bin/env python3
"""
Train Home-Type-Specific Models

Train separate models for each home type and compare performance.
Used for identifying home-type-specific failure patterns.

Epic 46 Enhancement: Home-Type-Specific Model Training
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Import with proper path handling
from src.core.database import initialize_database
from src.core.predictive_analytics import PredictiveAnalyticsEngine
from src.config import Settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

HOME_TYPES = [
    'single_family_house',
    'apartment',
    'condo',
    'townhouse',
    'cottage',
    'studio',
    'multi_story',
    'ranch_house'
]


async def train_home_type_model(
    home_type: str,
    data_file: Path,
    models_dir: Path,
    days_back: int = 180
) -> dict[str, Any]:
    """
    Train a model for a specific home type.
    
    Args:
        home_type: Home type name
        data_file: Path to JSON file with home-type-specific data
        models_dir: Directory to save models
        days_back: Number of days of historical data
    
    Returns:
        Dictionary with model performance metrics
    """
    logger.info(f"\n{'=' * 80}")
    logger.info(f"Training model for: {home_type}")
    logger.info(f"{'=' * 80}")
    
    try:
        # Load home-type-specific data
        with open(data_file, 'r', encoding='utf-8') as f:
            all_data = json.load(f)
        
        # Filter for this home type
        home_type_data = [d for d in all_data if d.get('home_type') == home_type]
        
        if not home_type_data:
            logger.warning(f"No data found for {home_type}, skipping...")
            return {}
        
        logger.info(f"Loaded {len(home_type_data)} samples for {home_type}")
        
        # Initialize database and engine
        settings = Settings()
        await initialize_database(settings)
        
        # Create engine with custom models directory
        engine = PredictiveAnalyticsEngine(settings)
        original_models_dir = engine.models_dir
        engine.models_dir = str(models_dir / home_type)
        Path(engine.models_dir).mkdir(parents=True, exist_ok=True)
        
        # Train model
        logger.info(f"Training model with {len(home_type_data)} samples...")
        await engine.train_models(historical_data=home_type_data, days_back=days_back)
        
        # Get performance metrics
        performance = {
            'home_type': home_type,
            'sample_count': len(home_type_data),
            'model_performance': engine.model_performance.copy(),
            'model_metadata': engine.model_metadata.copy()
        }
        
        # Restore original models directory
        engine.models_dir = original_models_dir
        
        logger.info(f"✅ Model trained for {home_type}")
        logger.info(f"   Accuracy: {performance['model_performance'].get('accuracy', 0):.3f}")
        logger.info(f"   Precision: {performance['model_performance'].get('precision', 0):.3f}")
        logger.info(f"   Recall: {performance['model_performance'].get('recall', 0):.3f}")
        logger.info(f"   F1 Score: {performance['model_performance'].get('f1_score', 0):.3f}")
        
        return performance
        
    except Exception as e:
        logger.error(f"❌ Failed to train model for {home_type}: {e}", exc_info=True)
        return {}


async def train_all_home_type_models(
    data_file: Path,
    output_dir: Path | None = None,
    days_back: int = 180
) -> dict[str, dict[str, Any]]:
    """
    Train models for all home types.
    
    Args:
        data_file: Path to JSON file with all home-type data
        output_dir: Directory to save models (default: data/models/home_type_models)
        days_back: Number of days of historical data
    
    Returns:
        Dictionary mapping home_type to performance metrics
    """
    if output_dir is None:
        output_dir = Path("data/models/home_type_models")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("=" * 80)
    logger.info("Training Home-Type-Specific Models")
    logger.info("=" * 80)
    logger.info(f"Data file: {data_file}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Days back: {days_back}")
    logger.info("")
    
    results = {}
    
    # Train model for each home type
    for home_type in HOME_TYPES:
        performance = await train_home_type_model(
            home_type=home_type,
            data_file=data_file,
            models_dir=output_dir,
            days_back=days_back
        )
        
        if performance:
            results[home_type] = performance
    
    return results


def compare_home_type_models(results: dict[str, dict[str, Any]]) -> None:
    """
    Compare performance across home types.
    
    Args:
        results: Dictionary mapping home_type to performance metrics
    """
    logger.info(f"\n{'=' * 80}")
    logger.info("Home-Type Model Comparison")
    logger.info(f"{'=' * 80}")
    
    if not results:
        logger.warning("No results to compare")
        return
    
    # Create comparison table
    logger.info("\nPerformance by Home Type:")
    logger.info(f"{'Home Type':<20} {'Samples':<10} {'Accuracy':<10} {'Precision':<10} {'Recall':<10} {'F1':<10}")
    logger.info("-" * 80)
    
    for home_type, perf in sorted(results.items(), key=lambda x: x[1]['model_performance'].get('accuracy', 0), reverse=True):
        mp = perf['model_performance']
        logger.info(
            f"{home_type:<20} "
            f"{perf['sample_count']:<10} "
            f"{mp.get('accuracy', 0):<10.3f} "
            f"{mp.get('precision', 0):<10.3f} "
            f"{mp.get('recall', 0):<10.3f} "
            f"{mp.get('f1_score', 0):<10.3f}"
        )
    
    # Calculate averages
    avg_accuracy = sum(r['model_performance'].get('accuracy', 0) for r in results.values()) / len(results)
    avg_precision = sum(r['model_performance'].get('precision', 0) for r in results.values()) / len(results)
    avg_recall = sum(r['model_performance'].get('recall', 0) for r in results.values()) / len(results)
    avg_f1 = sum(r['model_performance'].get('f1_score', 0) for r in results.values()) / len(results)
    
    logger.info("-" * 80)
    logger.info(
        f"{'Average':<20} "
        f"{'':<10} "
        f"{avg_accuracy:<10.3f} "
        f"{avg_precision:<10.3f} "
        f"{avg_recall:<10.3f} "
        f"{avg_f1:<10.3f}"
    )
    
    # Identify best and worst performers
    best = max(results.items(), key=lambda x: x[1]['model_performance'].get('accuracy', 0))
    worst = min(results.items(), key=lambda x: x[1]['model_performance'].get('accuracy', 0))
    
    logger.info(f"\nBest performer: {best[0]} (Accuracy: {best[1]['model_performance'].get('accuracy', 0):.3f})")
    logger.info(f"Worst performer: {worst[0]} (Accuracy: {worst[1]['model_performance'].get('accuracy', 0):.3f})")


async def main():
    """Main CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Train home-type-specific models and compare performance'
    )
    parser.add_argument(
        '--data-file',
        type=str,
        default='data/synthetic_datasets/synthetic_devices_all_home_types.json',
        help='Path to JSON file with home-type data (default: data/synthetic_datasets/synthetic_devices_all_home_types.json)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='data/models/home_type_models',
        help='Directory to save models (default: data/models/home_type_models)'
    )
    parser.add_argument(
        '--days-back',
        type=int,
        default=180,
        help='Number of days of historical data (default: 180)'
    )
    
    args = parser.parse_args()
    
    data_file = Path(args.data_file)
    if not data_file.exists():
        logger.error(f"Data file not found: {data_file}")
        return 1
    
    try:
        results = await train_all_home_type_models(
            data_file=data_file,
            output_dir=Path(args.output_dir),
            days_back=args.days_back
        )
        
        compare_home_type_models(results)
        
        # Save comparison results
        results_file = Path(args.output_dir) / "comparison_results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"\n✅ Comparison results saved to: {results_file}")
        logger.info(f"\n{'=' * 80}")
        logger.info("✅ Training Complete!")
        logger.info(f"{'=' * 80}")
        
        return 0
    except Exception as e:
        logger.error(f"❌ Training failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))

