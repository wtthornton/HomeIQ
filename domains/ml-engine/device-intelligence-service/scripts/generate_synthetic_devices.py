#!/usr/bin/env python3
"""
Generate Synthetic Device Data

Standalone CLI tool for generating synthetic device training data.
Used for initial model training before alpha release.

Epic 46, Story 46.1: Synthetic Device Data Generator
"""

import argparse
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


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Generate synthetic device training data (template-based, no API costs)'
    )
    parser.add_argument(
        '--count',
        type=int,
        default=1000,
        help='Number of device samples to generate (default: 1000)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=180,
        help='Number of days of historical data to simulate (default: 180)'
    )
    parser.add_argument(
        '--failure-rate',
        type=float,
        default=0.15,
        help='Percentage of devices with failure scenarios (0.0-1.0, default: 0.15)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output JSON file path (default: print to stdout)'
    )
    parser.add_argument(
        '--seed',
        type=int,
        help='Random seed for reproducibility'
    )
    parser.add_argument(
        '--device-types',
        nargs='+',
        choices=['sensor', 'switch', 'light', 'climate', 'security', 'battery_powered', 'media', 'vacuum'],
        help='Specific device types to generate (default: all types)'
    )
    parser.add_argument(
        '--home-type',
        type=str,
        choices=['single_family_house', 'apartment', 'condo', 'townhouse', 'cottage', 'studio', 'multi_story', 'ranch_house'],
        help='Home type to influence device distribution (default: generic)'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.count < 1:
        logger.error("Count must be at least 1")
        return 1
    
    if args.days < 1:
        logger.error("Days must be at least 1")
        return 1
    
    if not (0.0 <= args.failure_rate <= 1.0):
        logger.error("Failure rate must be between 0.0 and 1.0")
        return 1
    
    # Generate synthetic data
    logger.info(f"Generating {args.count} synthetic device samples...")
    logger.info(f"  - Days: {args.days}")
    logger.info(f"  - Failure rate: {args.failure_rate:.1%}")
    logger.info(f"  - Device types: {args.device_types or 'all'}")
    logger.info(f"  - Home type: {args.home_type or 'default'}")
    
    generator = SyntheticDeviceGenerator(random_seed=args.seed, home_type=args.home_type)
    training_data = generator.generate_training_data(
        count=args.count,
        days=args.days,
        failure_rate=args.failure_rate,
        device_types=args.device_types,
        home_type=args.home_type
    )
    
    # Output results
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(training_data, f, indent=2)
        
        logger.info(f"✅ Generated {len(training_data)} samples")
        logger.info(f"✅ Saved to: {output_path}")
        logger.info(f"   File size: {output_path.stat().st_size / 1024:.1f} KB")
    else:
        # Print to stdout as JSON
        print(json.dumps(training_data, indent=2))
        logger.info(f"✅ Generated {len(training_data)} samples (printed to stdout)")
    
    # Print statistics
    logger.info("\n📊 Generation Statistics:")
    logger.info(f"  - Total samples: {len(training_data)}")
    logger.info(f"  - Unique devices: {len(set(d['device_id'] for d in training_data))}")
    
    # Calculate averages
    avg_response_time = sum(d['response_time'] for d in training_data) / len(training_data)
    avg_error_rate = sum(d['error_rate'] for d in training_data) / len(training_data)
    avg_battery = sum(d['battery_level'] for d in training_data) / len(training_data)
    
    logger.info(f"  - Avg response time: {avg_response_time:.1f} ms")
    logger.info(f"  - Avg error rate: {avg_error_rate:.4f}")
    logger.info(f"  - Avg battery level: {avg_battery:.1f}%")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

