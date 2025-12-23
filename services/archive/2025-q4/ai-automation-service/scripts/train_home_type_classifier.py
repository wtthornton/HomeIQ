"""
Script to train home type classifier on synthetic homes.

Usage:
    python scripts/train_home_type_classifier.py --synthetic-homes tests/datasets/synthetic_homes --output models/home_type_classifier.pkl
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.home_type.home_type_classifier import FineTunedHomeTypeClassifier

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main function to train classifier."""
    parser = argparse.ArgumentParser(description='Train home type classifier')
    parser.add_argument(
        '--synthetic-homes',
        type=str,
        required=True,
        help='Directory containing synthetic homes JSON files'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='models/home_type_classifier.pkl',
        help='Output path for trained model (default: models/home_type_classifier.pkl)'
    )
    parser.add_argument(
        '--test-size',
        type=float,
        default=0.2,
        help='Test set size (default: 0.2)'
    )
    
    args = parser.parse_args()
    
    # Load synthetic homes
    homes_dir = Path(args.synthetic_homes)
    if not homes_dir.exists():
        logger.error(f"❌ Synthetic homes directory not found: {homes_dir}")
        return 1
    
    # Find all home JSON files
    home_files = list(homes_dir.glob("home_*.json"))
    if not home_files:
        logger.error(f"❌ No home JSON files found in {homes_dir}")
        return 1
    
    logger.info(f"Loading {len(home_files)} synthetic homes...")
    
    synthetic_homes = []
    for home_file in home_files:
        try:
            with open(home_file, 'r', encoding='utf-8') as f:
                home = json.load(f)
                synthetic_homes.append(home)
        except Exception as e:
            logger.error(f"Failed to load {home_file}: {e}")
            continue
    
    if not synthetic_homes:
        logger.error("❌ No valid synthetic homes loaded")
        return 1
    
    logger.info(f"✅ Loaded {len(synthetic_homes)} synthetic homes")
    
    # Initialize classifier
    classifier = FineTunedHomeTypeClassifier()
    
    # Train model
    logger.info("Starting model training...")
    results = await classifier.train_from_synthetic_data(
        synthetic_homes=synthetic_homes,
        test_size=args.test_size
    )
    
    # Save model
    output_path = Path(args.output)
    classifier.save(output_path)
    
    # Save training results
    results_path = output_path.parent / f"{output_path.stem}_results.json"
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"✅ Training results saved to {results_path}")
    
    # Print summary
    print("\n" + "="*60)
    print("TRAINING SUMMARY")
    print("="*60)
    print(f"Accuracy: {results['accuracy']:.3f}")
    print(f"Precision: {results['precision']:.3f}")
    print(f"Recall: {results['recall']:.3f}")
    print(f"F1 Score: {results['f1_score']:.3f}")
    print(f"CV Accuracy: {results['cv_accuracy_mean']:.3f} ± {results['cv_accuracy_std']:.3f}")
    print(f"\nTraining samples: {results['training_samples']}")
    print(f"Test samples: {results['test_samples']}")
    print(f"\nClasses: {', '.join(results['class_names'])}")
    print(f"\nModel saved to: {output_path}")
    print("="*60)
    
    # Feature importance
    feature_importance = classifier.get_feature_importance()
    if feature_importance:
        print("\nTop 10 Feature Importance:")
        sorted_features = sorted(
            feature_importance.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        for feature, importance in sorted_features:
            print(f"  {feature}: {importance:.4f}")
    
    return 0


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

