#!/usr/bin/env python3
"""
Generate Synthetic Device Data by Home Type

Generate stratified datasets for each home type (500 samples per type).
Used for home-type-specific model training and validation.

Epic 46 Enhancement: Home-Type-Aware Data Generation
"""

import json
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from training.synthetic_device_generator import SyntheticDeviceGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Home types to generate
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


def generate_home_type_datasets(
    samples_per_type: int = 500,
    days: int = 180,
    failure_rate: float = 0.15,
    output_dir: Path | None = None
) -> dict[str, Path]:
    """
    Generate synthetic device data for each home type.
    
    Args:
        samples_per_type: Number of samples to generate per home type
        days: Number of days of historical data
        failure_rate: Percentage of devices with failure scenarios
        output_dir: Directory to save output files (default: current directory)
    
    Returns:
        Dictionary mapping home_type to output file path
    """
    if output_dir is None:
        output_dir = Path.cwd()
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("=" * 80)
    logger.info("Generating Home-Type-Specific Datasets")
    logger.info("=" * 80)
    logger.info(f"Samples per home type: {samples_per_type}")
    logger.info(f"Total samples: {samples_per_type * len(HOME_TYPES)}")
    logger.info(f"Days: {days}")
    logger.info(f"Failure rate: {failure_rate:.1%}")
    logger.info("")
    
    output_files = {}
    
    for home_type in HOME_TYPES:
        logger.info(f"\n{'=' * 80}")
        logger.info(f"Generating data for: {home_type}")
        logger.info(f"{'=' * 80}")
        
        try:
            generator = SyntheticDeviceGenerator(home_type=home_type)
            training_data = generator.generate_training_data(
                count=samples_per_type,
                days=days,
                failure_rate=failure_rate,
                home_type=home_type
            )
            
            # Save to file
            output_file = output_dir / f"synthetic_devices_{home_type}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(training_data, f, indent=2)
            
            file_size_kb = output_file.stat().st_size / 1024
            logger.info(f"✅ Generated {len(training_data)} samples for {home_type}")
            logger.info(f"✅ Saved to: {output_file}")
            logger.info(f"   File size: {file_size_kb:.1f} KB")
            
            # Calculate statistics
            avg_response_time = sum(d['response_time'] for d in training_data) / len(training_data)
            avg_error_rate = sum(d['error_rate'] for d in training_data) / len(training_data)
            avg_battery = sum(d['battery_level'] for d in training_data) / len(training_data)
            
            logger.info(f"   Avg response time: {avg_response_time:.1f} ms")
            logger.info(f"   Avg error rate: {avg_error_rate:.4f}")
            logger.info(f"   Avg battery level: {avg_battery:.1f}%")
            
            output_files[home_type] = output_file
            
        except Exception as e:
            logger.error(f"❌ Failed to generate data for {home_type}: {e}", exc_info=True)
            continue
    
    # Generate combined dataset
    logger.info(f"\n{'=' * 80}")
    logger.info("Generating Combined Dataset")
    logger.info(f"{'=' * 80}")
    
    all_data = []
    for home_type, output_file in output_files.items():
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Add home_type metadata to each sample
            for sample in data:
                sample['home_type'] = home_type
            all_data.extend(data)
    
    combined_file = output_dir / "synthetic_devices_all_home_types.json"
    with open(combined_file, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, indent=2)
    
    file_size_kb = combined_file.stat().st_size / 1024
    logger.info(f"✅ Generated combined dataset: {len(all_data)} samples")
    logger.info(f"✅ Saved to: {combined_file}")
    logger.info(f"   File size: {file_size_kb:.1f} KB")
    
    output_files['combined'] = combined_file
    
    logger.info(f"\n{'=' * 80}")
    logger.info("✅ Generation Complete!")
    logger.info(f"{'=' * 80}")
    logger.info(f"Total samples generated: {len(all_data)}")
    logger.info(f"Files created: {len(output_files)}")
    
    return output_files


def main():
    """Main CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generate synthetic device data stratified by home type'
    )
    parser.add_argument(
        '--samples-per-type',
        type=int,
        default=500,
        help='Number of samples to generate per home type (default: 500)'
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
        '--output-dir',
        type=str,
        default='.',
        help='Output directory for generated files (default: current directory)'
    )
    
    args = parser.parse_args()
    
    try:
        output_files = generate_home_type_datasets(
            samples_per_type=args.samples_per_type,
            days=args.days,
            failure_rate=args.failure_rate,
            output_dir=Path(args.output_dir)
        )
        return 0
    except Exception as e:
        logger.error(f"❌ Generation failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())

