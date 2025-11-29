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
from src.training.synthetic_device_generator import SyntheticDeviceGenerator
from src.training.synthetic_event_generator import SyntheticEventGenerator
from src.training.synthetic_external_data_generator import SyntheticExternalDataGenerator
from src.training.synthetic_home_generator import SyntheticHomeGenerator

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
    parser.add_argument(
        '--enable-weather',
        action='store_true',
        default=True,
        help='Enable weather data generation (default: True)'
    )
    parser.add_argument(
        '--disable-weather',
        action='store_false',
        dest='enable_weather',
        help='Disable weather data generation'
    )
    parser.add_argument(
        '--enable-carbon',
        action='store_true',
        default=True,
        help='Enable carbon intensity data generation (default: True)'
    )
    parser.add_argument(
        '--disable-carbon',
        action='store_false',
        dest='enable_carbon',
        help='Disable carbon intensity data generation'
    )
    parser.add_argument(
        '--enable-pricing',
        action='store_true',
        default=True,
        help='Enable electricity pricing data generation (default: True)'
    )
    parser.add_argument(
        '--disable-pricing',
        action='store_false',
        dest='enable_pricing',
        help='Disable electricity pricing data generation'
    )
    parser.add_argument(
        '--enable-calendar',
        action='store_true',
        default=True,
        help='Enable calendar data generation (default: True)'
    )
    parser.add_argument(
        '--disable-calendar',
        action='store_false',
        dest='enable_calendar',
        help='Disable calendar data generation'
    )
    
    args = parser.parse_args()
    
    # Initialize generators
    area_generator = SyntheticAreaGenerator()
    device_generator = SyntheticDeviceGenerator()
    event_generator = SyntheticEventGenerator()
    external_data_generator = SyntheticExternalDataGenerator()
    
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
    total_homes = len(homes)
    
    logger.info(f"📊 Starting generation for {total_homes} homes ({args.days} days each)")
    logger.info("="*80)
    
    import time
    generation_start_time = time.time()
    
    for i, home in enumerate(homes):
        home_num = i + 1
        logger.info(f"🏠 [{home_num}/{total_homes}] Processing home: {home['home_type']}")
        
        try:
            # Generate areas (template-based)
            logger.debug(f"   [{home_num}/{total_homes}] Generating areas...")
            areas = area_generator.generate_areas(home)
            home['areas'] = areas
            logger.debug(f"   [{home_num}/{total_homes}] Generated {len(areas)} areas")
            
            # Generate devices (template-based)
            logger.debug(f"   [{home_num}/{total_homes}] Generating devices...")
            devices = device_generator.generate_devices(home, areas)
            home['devices'] = devices
            logger.debug(f"   [{home_num}/{total_homes}] Generated {len(devices)} devices")
            
            # Generate events (local computation)
            logger.info(f"   [{home_num}/{total_homes}] Generating {args.days} days of events for {len(devices)} devices... (this may take a while)")
            
            # Progress callback for event generation (show at INFO level for visibility)
            def event_progress(device_num, total_devices, days_processed, total_days):
                device_pct = (device_num / total_devices) * 100
                day_pct = (days_processed / total_days) * 100
                # Log at INFO level for important milestones, DEBUG for frequent updates
                if device_num == total_devices or days_processed == total_days or (device_num % 10 == 0 and days_processed % 10 == 0):
                    logger.info(f"      [{home_num}/{total_homes}] Events progress: {device_num}/{total_devices} devices ({device_pct:.0f}%), {days_processed}/{total_days} days ({day_pct:.0f}%)")
                else:
                    logger.debug(f"      [{home_num}/{total_homes}] Events: {device_num}/{total_devices} devices ({device_pct:.0f}%), {days_processed}/{total_days} days ({day_pct:.0f}%)")
            
            events = await event_generator.generate_events(devices, days=args.days, progress_callback=event_progress)
            home['events'] = events
            logger.info(f"   [{home_num}/{total_homes}] Generated {len(events)} events")
            
            # Generate external data only if at least one is enabled
            final_events = events
            external_data = {}
            
            if args.enable_weather or args.enable_carbon or args.enable_pricing or args.enable_calendar:
                from datetime import datetime, timedelta, timezone
                start_date = datetime.now(timezone.utc) - timedelta(days=args.days)
                
                # Generate unified external data (generator always generates all types)
                external_data = external_data_generator.generate_external_data(
                    home=home,
                    start_date=start_date,
                    days=args.days
                )
                
                # Filter external data based on enable flags
                if not args.enable_weather:
                    external_data['weather'] = []
                if not args.enable_carbon:
                    external_data['carbon_intensity'] = []
                if not args.enable_pricing:
                    external_data['pricing'] = []
                if not args.enable_calendar:
                    external_data['calendar'] = []
                
                # Apply correlations to events (if weather/carbon data available)
                if args.enable_weather and external_data.get('weather'):
                    from src.training.synthetic_weather_generator import SyntheticWeatherGenerator
                    weather_gen = SyntheticWeatherGenerator()
                    final_events = weather_gen.correlate_with_hvac(
                        external_data['weather'],
                        final_events,
                        devices
                    )
                    final_events = weather_gen.correlate_with_windows(
                        external_data['weather'],
                        final_events,
                        devices
                    )
                
                if args.enable_carbon and external_data.get('carbon_intensity'):
                    from src.training.synthetic_carbon_intensity_generator import SyntheticCarbonIntensityGenerator
                    carbon_gen = SyntheticCarbonIntensityGenerator()
                    final_events = carbon_gen.correlate_with_energy_devices(
                        external_data['carbon_intensity'],
                        final_events,
                        devices
                    )
            
            # Update events with correlations
            home['events'] = final_events
            
            # Add external_data section to home
            home['external_data'] = external_data
            
            complete_homes.append(home)
            
            # Log external data summary
            weather_count = len(external_data.get('weather', []))
            carbon_count = len(external_data.get('carbon_intensity', []))
            pricing_count = len(external_data.get('pricing', []))
            calendar_count = len(external_data.get('calendar', []))
            
            logger.info(
                f"✅ [{home_num}/{total_homes}] Completed: {len(devices)} devices, {len(final_events)} events, "
                f"weather={weather_count}, carbon={carbon_count}, pricing={pricing_count}, calendar={calendar_count}"
            )
            
            # Progress update every 10 homes or on last home (more frequent for smaller runs)
            progress_interval = 10 if total_homes >= 50 else 5
            if home_num % progress_interval == 0 or home_num == total_homes:
                progress_pct = (home_num / total_homes) * 100
                elapsed_msg = ""
                if home_num > 0:
                    elapsed_time = time.time() - generation_start_time
                    if elapsed_time > 0:
                        avg_time_per_home = elapsed_time / home_num
                        remaining_homes = total_homes - home_num
                        estimated_remaining = avg_time_per_home * remaining_homes
                        elapsed_min = elapsed_time / 60
                        remaining_min = estimated_remaining / 60
                        elapsed_msg = f" | Elapsed: {elapsed_min:.1f} min | ETA: {remaining_min:.1f} min"
                logger.info(f"📈 Progress: {home_num}/{total_homes} homes ({progress_pct:.1f}%){elapsed_msg}")
            
            # Flush output to ensure real-time visibility
            import sys
            sys.stdout.flush()
            
        except Exception as e:
            logger.error(f"❌ [{home_num}/{total_homes}] Failed to process home: {e}")
            import traceback
            logger.debug(traceback.format_exc())
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
    total_pricing_points = sum(len(h.get('external_data', {}).get('pricing', [])) for h in complete_homes)
    total_calendar_points = sum(len(h.get('external_data', {}).get('calendar', [])) for h in complete_homes)
    
    print(f"\nTotal devices: {total_devices}")
    print(f"Total events: {total_events}")
    print(f"Total weather data points: {total_weather_points}")
    print(f"Total carbon intensity data points: {total_carbon_points}")
    print(f"Total pricing data points: {total_pricing_points}")
    print(f"Total calendar events: {total_calendar_points}")
    
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

