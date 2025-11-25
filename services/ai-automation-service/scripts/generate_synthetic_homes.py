"""
Script to generate synthetic homes for home type categorization training.

Usage:
    python scripts/generate_synthetic_homes.py --count 100 --output tests/datasets/synthetic_homes
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import settings
from llm.openai_client import OpenAIClient
from training.synthetic_area_generator import SyntheticAreaGenerator
from training.synthetic_device_generator import SyntheticDeviceGenerator
from training.synthetic_event_generator import SyntheticEventGenerator
from training.synthetic_home_generator import SyntheticHomeGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main function to generate synthetic homes."""
    parser = argparse.ArgumentParser(description='Generate synthetic homes for training')
    parser.add_argument(
        '--count',
        type=int,
        default=100,
        help='Number of homes to generate (default: 100)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='tests/datasets/synthetic_homes',
        help='Output directory for synthetic homes (default: tests/datasets/synthetic_homes)'
    )
    parser.add_argument(
        '--home-types',
        nargs='+',
        help='Specific home types to generate (optional)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Number of days of events to generate per home (default: 7)'
    )
    
    args = parser.parse_args()
    
    # Initialize OpenAI client
    if not settings.openai_api_key:
        logger.error("❌ OPENAI_API_KEY not set in environment")
        return 1
    
    openai_client = OpenAIClient(
        api_key=settings.openai_api_key,
        model='gpt-4o-mini'  # Use cheaper model for generation
    )
    
    # Initialize generators
    home_generator = SyntheticHomeGenerator(openai_client)
    area_generator = SyntheticAreaGenerator(openai_client)
    device_generator = SyntheticDeviceGenerator(openai_client)
    event_generator = SyntheticEventGenerator()
    
    logger.info(f"🚀 Starting synthetic home generation: {args.count} homes")
    
    # Generate homes
    homes = await home_generator.generate_homes(
        target_count=args.count,
        home_types=args.home_types
    )
    
    if not homes:
        logger.error("❌ No homes generated")
        return 1
    
    # Generate areas, devices, and events for each home
    complete_homes = []
    
    for i, home in enumerate(homes):
        logger.info(f"Processing home {i+1}/{len(homes)}: {home['home_type']}")
        
        try:
            # Generate areas
            areas = await area_generator.generate_areas(home)
            home['areas'] = areas
            
            # Generate devices
            devices = await device_generator.generate_devices(home, areas)
            home['devices'] = devices
            
            # Generate events
            events = await event_generator.generate_events(devices, days=args.days)
            home['events'] = events
            
            complete_homes.append(home)
            logger.info(f"✅ Completed home {i+1}/{len(homes)}: {len(devices)} devices, {len(events)} events")
            
        except Exception as e:
            logger.error(f"❌ Failed to process home {i+1}: {e}")
            continue
    
    # Save homes
    output_path = Path(args.output)
    await home_generator.save_homes(complete_homes, output_path)
    
    logger.info(f"✅ Generation complete: {len(complete_homes)} homes saved to {output_path}")
    
    # Print summary
    print("\n" + "="*60)
    print("GENERATION SUMMARY")
    print("="*60)
    print(f"Total homes generated: {len(complete_homes)}")
    print(f"Output directory: {output_path}")
    
    # Home type breakdown
    home_types = {}
    for home in complete_homes:
        ht = home['home_type']
        home_types[ht] = home_types.get(ht, 0) + 1
    
    print("\nHome type distribution:")
    for ht, count in sorted(home_types.items()):
        print(f"  {ht}: {count}")
    
    # Device and event totals
    total_devices = sum(len(h.get('devices', [])) for h in complete_homes)
    total_events = sum(len(h.get('events', [])) for h in complete_homes)
    
    print(f"\nTotal devices: {total_devices}")
    print(f"Total events: {total_events}")
    print("="*60)
    
    return 0


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

