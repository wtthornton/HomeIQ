#!/usr/bin/env python3
"""
Generate Large-Scale Synthetic Device Dataset

Generate 10,000+ samples with diverse home types and enhanced temporal patterns.
Used for advanced model training and production deployment.

Epic 46 Enhancement: Scale Up to 10,000+ Samples
"""

import json
import logging
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from training.synthetic_device_generator import SyntheticDeviceGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Home type distribution (realistic proportions)
HOME_TYPE_DISTRIBUTION = {
    'single_family_house': 0.35,  # Most common
    'apartment': 0.20,
    'condo': 0.15,
    'townhouse': 0.12,
    'ranch_house': 0.08,
    'multi_story': 0.05,
    'cottage': 0.03,
    'studio': 0.02
}


def generate_large_dataset(
    total_samples: int = 10000,
    days: int = 180,
    failure_rate: float = 0.15,
    output_file: Path | None = None,
    use_temporal_patterns: bool = True
) -> list[dict]:
    """
    Generate large-scale synthetic device dataset with diverse home types.
    
    Args:
        total_samples: Total number of samples to generate
        days: Number of days of historical data
        failure_rate: Percentage of devices with failure scenarios
        output_file: Output JSON file path
        use_temporal_patterns: Whether to use enhanced temporal patterns (2025)
    
    Returns:
        List of device metric dictionaries
    """
    if output_file is None:
        output_file = Path("data/synthetic_datasets/large_training_data.json")
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info("=" * 80)
    logger.info("Generating Large-Scale Synthetic Device Dataset")
    logger.info("=" * 80)
    logger.info(f"Total samples: {total_samples:,}")
    logger.info(f"Days: {days}")
    logger.info(f"Failure rate: {failure_rate:.1%}")
    logger.info(f"Temporal patterns: {use_temporal_patterns}")
    logger.info("")
    
    all_samples = []
    home_types = list(HOME_TYPE_DISTRIBUTION.keys())
    
    # Calculate samples per home type
    samples_per_type = {}
    remaining = total_samples
    for i, home_type in enumerate(home_types):
        if i == len(home_types) - 1:
            # Last type gets remaining samples
            samples_per_type[home_type] = remaining
        else:
            count = int(total_samples * HOME_TYPE_DISTRIBUTION[home_type])
            samples_per_type[home_type] = count
            remaining -= count
    
    # Generate samples for each home type
    reference_date = datetime.now(timezone.utc) if use_temporal_patterns else None
    
    for home_type, count in samples_per_type.items():
        if count == 0:
            continue
        
        logger.info(f"\nGenerating {count:,} samples for {home_type}...")
        
        generator = SyntheticDeviceGenerator(home_type=home_type)
        
        # Vary reference date slightly for diversity (2025: temporal diversity)
        if use_temporal_patterns:
            # Spread dates over the past 30 days for temporal diversity
            days_offset = random.randint(0, 30)
            type_reference_date = reference_date - timedelta(days=days_offset)
        else:
            type_reference_date = None
        
        samples = generator.generate_training_data(
            count=count,
            days=days,
            failure_rate=failure_rate,
            home_type=home_type,
            reference_date=type_reference_date
        )
        
        # Add home_type metadata
        for sample in samples:
            sample['home_type'] = home_type
        
        all_samples.extend(samples)
        logger.info(f"  ✅ Generated {len(samples):,} samples for {home_type}")
    
    # Shuffle for better training distribution
    random.shuffle(all_samples)
    
    # Save to file
    logger.info(f"\n{'=' * 80}")
    logger.info("Saving dataset...")
    logger.info(f"{'=' * 80}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_samples, f, indent=2)
    
    file_size_mb = output_file.stat().st_size / (1024 * 1024)
    logger.info(f"✅ Saved {len(all_samples):,} samples to: {output_file}")
    logger.info(f"   File size: {file_size_mb:.2f} MB")
    
    # Calculate statistics
    logger.info(f"\n{'=' * 80}")
    logger.info("Dataset Statistics")
    logger.info(f"{'=' * 80}")
    logger.info(f"Total samples: {len(all_samples):,}")
    
    # Home type distribution
    home_type_counts = {}
    for sample in all_samples:
        ht = sample.get('home_type', 'unknown')
        home_type_counts[ht] = home_type_counts.get(ht, 0) + 1
    
    logger.info("\nHome type distribution:")
    for home_type, count in sorted(home_type_counts.items(), key=lambda x: -x[1]):
        pct = (count / len(all_samples)) * 100
        logger.info(f"  {home_type:20s}: {count:5,} ({pct:5.1f}%)")
    
    # Average metrics
    avg_response_time = sum(d['response_time'] for d in all_samples) / len(all_samples)
    avg_error_rate = sum(d['error_rate'] for d in all_samples) / len(all_samples)
    avg_battery = sum(d['battery_level'] for d in all_samples) / len(all_samples)
    
    logger.info(f"\nAverage metrics:")
    logger.info(f"  Response time: {avg_response_time:.1f} ms")
    logger.info(f"  Error rate: {avg_error_rate:.4f}")
    logger.info(f"  Battery level: {avg_battery:.1f}%")
    
    return all_samples


def main():
    """Main CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generate large-scale synthetic device dataset (10,000+ samples)'
    )
    parser.add_argument(
        '--samples',
        type=int,
        default=10000,
        help='Total number of samples to generate (default: 10000)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=180,
        help='Number of days of historical data (default: 180)'
    )
    parser.add_argument(
        '--failure-rate',
        type=float,
        default=0.15,
        help='Percentage of devices with failure scenarios (default: 0.15)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='data/synthetic_datasets/large_training_data.json',
        help='Output file path (default: data/synthetic_datasets/large_training_data.json)'
    )
    parser.add_argument(
        '--no-temporal',
        action='store_true',
        help='Disable enhanced temporal patterns'
    )
    
    args = parser.parse_args()
    
    try:
        samples = generate_large_dataset(
            total_samples=args.samples,
            days=args.days,
            failure_rate=args.failure_rate,
            output_file=Path(args.output),
            use_temporal_patterns=not args.no_temporal
        )
        logger.info(f"\n{'=' * 80}")
        logger.info("✅ Generation Complete!")
        logger.info(f"{'=' * 80}")
        return 0
    except Exception as e:
        logger.error(f"❌ Generation failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())

