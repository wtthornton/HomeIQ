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
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.training.synthetic_area_generator import SyntheticAreaGenerator
from src.training.synthetic_carbon_intensity_generator import SyntheticCarbonIntensityGenerator
from src.training.synthetic_device_generator import SyntheticDeviceGenerator
from src.training.synthetic_event_generator import SyntheticEventGenerator
from src.training.synthetic_home_generator import SyntheticHomeGenerator
from src.training.synthetic_weather_generator import SyntheticWeatherGenerator

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
        default=90,
        help='Number of days of events to generate per home (default: 90)'
    )
    parser.add_argument(
        '--enable-openai',
        action='store_true',
        help='Enable OpenAI enhancement (20%% enhanced, 80%% template-based)'
    )
    parser.add_argument(
        '--enhancement-percentage',
        type=float,
        default=0.20,
        help='Percentage of homes to generate with OpenAI (default: 0.20)'
    )
    parser.add_argument(
        '--validate-percentage',
        type=float,
        default=0.10,
        help='Percentage of template homes to validate with OpenAI (default: 0.10)'
    )
    
    args = parser.parse_args()
    
    # Initialize generators
    area_generator = SyntheticAreaGenerator()
    device_generator = SyntheticDeviceGenerator()
    event_generator = SyntheticEventGenerator()
    weather_generator = SyntheticWeatherGenerator()
    carbon_generator = SyntheticCarbonIntensityGenerator()
    
    # Initialize home generator with optional OpenAI enhancement
    if args.enable_openai:
        from src.llm.openai_client import OpenAIClient
        from src.config import settings
        
        if not settings.openai_api_key:
            logger.error("❌ OpenAI API key not configured. Set OPENAI_API_KEY in .env")
            return 1
        
        logger.info("🚀 Starting synthetic home generation (hybrid: OpenAI-enhanced)")
        
        openai_client = OpenAIClient(
            api_key=settings.openai_api_key,
            model=settings.openai_model
        )
        
        home_generator = SyntheticHomeGenerator(
            enable_openai_enhancement=True,
            openai_client=openai_client
        )
        
        # Generate homes using hybrid approach
        homes = await home_generator.generate_homes_hybrid(
            target_count=args.count,
            home_types=args.home_types,
            enhancement_percentage=args.enhancement_percentage,
            validate_percentage=args.validate_percentage
        )
        
        # Log OpenAI usage stats
        if home_generator.openai_generator:
            stats = home_generator.openai_generator.get_stats()
            logger.info(f"OpenAI Generation Stats: {stats}")
            
            # Calculate costs (approximate)
            input_tokens = openai_client.total_input_tokens
            output_tokens = openai_client.total_output_tokens
            total_tokens = openai_client.total_tokens_used
            
            # GPT-5.1 pricing (approximate - adjust based on actual pricing)
            input_cost_per_1k = 0.15 / 1000  # $0.15 per 1M tokens
            output_cost_per_1k = 0.60 / 1000  # $0.60 per 1M tokens
            
            estimated_cost = (input_tokens * input_cost_per_1k) + (output_tokens * output_cost_per_1k)
            
            logger.info(f"OpenAI Token Usage:")
            logger.info(f"  - Input tokens: {input_tokens:,}")
            logger.info(f"  - Output tokens: {output_tokens:,}")
            logger.info(f"  - Total tokens: {total_tokens:,}")
            logger.info(f"  - Estimated cost: ${estimated_cost:.4f}")
            if len(homes) > 0:
                logger.info(f"  - Cost per home: ${estimated_cost / len(homes):.4f}")
    else:
        logger.info(f"🚀 Starting synthetic home generation (template-based): {args.count} homes")
        
        home_generator = SyntheticHomeGenerator()
        
        # Generate homes using template-only approach
        homes = home_generator.generate_homes(
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
            # Generate areas (template-based)
            areas = area_generator.generate_areas(home)
            home['areas'] = areas
            
            # Generate devices (template-based)
            devices = device_generator.generate_devices(home, areas)
            home['devices'] = devices
            
            # Generate events (local computation)
            events = await event_generator.generate_events(devices, days=args.days)
            home['events'] = events
            
            # Generate weather and carbon intensity data
            from datetime import datetime, timedelta, timezone
            start_date = datetime.now(timezone.utc) - timedelta(days=args.days)
            
            # Generate weather data
            weather_data = weather_generator.generate_weather(
                home,
                start_date,
                args.days
            )
            
            # Generate carbon intensity data
            carbon_data = carbon_generator.generate_carbon_intensity(
                home,
                start_date,
                args.days
            )
            
            # Correlate weather with HVAC and windows
            weather_correlated_events = weather_generator.correlate_with_hvac(
                weather_data,
                events,
                devices
            )
            weather_correlated_events = weather_generator.correlate_with_windows(
                weather_data,
                weather_correlated_events,
                devices
            )
            
            # Correlate carbon with energy devices
            final_events = carbon_generator.correlate_with_energy_devices(
                carbon_data,
                weather_correlated_events,
                devices
            )
            
            # Update events with correlations
            home['events'] = final_events
            
            # Add external_data section to home
            home['external_data'] = {
                'weather': weather_data,
                'carbon_intensity': carbon_data
            }
            
            complete_homes.append(home)
            logger.info(f"✅ Completed home {i+1}/{len(homes)}: {len(devices)} devices, {len(final_events)} events, {len(weather_data)} weather points, {len(carbon_data)} carbon points")
            
        except Exception as e:
            logger.error(f"❌ Failed to process home {i+1}: {e}")
            continue
    
    # Save homes
    output_path = Path(args.output)
    home_generator.save_homes(complete_homes, output_path)
    
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
    total_weather_points = sum(len(h.get('external_data', {}).get('weather', [])) for h in complete_homes)
    total_carbon_points = sum(len(h.get('external_data', {}).get('carbon_intensity', [])) for h in complete_homes)
    
    print(f"\nTotal devices: {total_devices}")
    print(f"Total events: {total_events}")
    print(f"Total weather data points: {total_weather_points}")
    print(f"Total carbon intensity data points: {total_carbon_points}")
    
    # OpenAI enhancement summary
    if args.enable_openai and home_generator.openai_generator:
        stats = home_generator.openai_generator.get_stats()
        input_tokens = home_generator.openai_client.total_input_tokens
        output_tokens = home_generator.openai_client.total_output_tokens
        total_tokens = home_generator.openai_client.total_tokens_used
        
        # GPT-5.1 pricing (approximate)
        input_cost_per_1k = 0.15 / 1000
        output_cost_per_1k = 0.60 / 1000
        estimated_cost = (input_tokens * input_cost_per_1k) + (output_tokens * output_cost_per_1k)
        
        print("\nOpenAI Enhancement Summary:")
        print(f"  - Enhanced homes: {stats.get('success_count', 0)}")
        print(f"  - Failed attempts: {stats.get('failure_count', 0)}")
        print(f"  - Total tokens: {total_tokens:,}")
        print(f"  - Input tokens: {input_tokens:,}")
        print(f"  - Output tokens: {output_tokens:,}")
        print(f"  - Estimated cost: ${estimated_cost:.4f}")
        if len(complete_homes) > 0:
            print(f"  - Cost per home: ${estimated_cost / len(complete_homes):.4f}")
    
    print("="*60)
    
    return 0


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

