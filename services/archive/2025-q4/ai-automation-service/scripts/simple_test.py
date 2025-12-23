#!/usr/bin/env python3
"""
Simple Preprocessing Test
"""

import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
SRC_PATH = CURRENT_DIR.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.append(str(SRC_PATH))

import time

from models.model_manager import get_model_manager
from preprocessing.event_preprocessor import EventPreprocessor


async def main():
    print("🧪 Testing Preprocessing Pipeline")
    print("=" * 50)

    # Create sample data
    from create_sample_data import create_sample_ha_events
    events_df = create_sample_ha_events(num_events=100, days_back=3)
    print(f"Generated {len(events_df)} events")

    # Initialize preprocessor
    model_manager = get_model_manager()
    preprocessor = EventPreprocessor(model_manager=model_manager)
    print("Preprocessor initialized")

    # Test preprocessing
    start_time = time.time()
    processed_events = await preprocessor.preprocess(events_df)
    processing_time = time.time() - start_time

    print(f"✅ Preprocessing completed in {processing_time:.2f}s")
    print(f"✅ Processed {len(processed_events.events)} events")
    print(f"✅ Total events: {processed_events.total_events}")
    print(f"✅ Unique devices: {processed_events.unique_devices}")
    print(f"✅ Unique sessions: {processed_events.unique_sessions}")

    # Check features
    sample_event = processed_events.events[0]
    print(f"✅ Sample event: {sample_event.device_name} at {sample_event.hour:02d}:{sample_event.minute:02d}")
    print(f"   - Day type: {sample_event.day_type}")
    print(f"   - Season: {sample_event.season}")
    print(f"   - Time of day: {sample_event.time_of_day}")
    print(f"   - Session: {sample_event.session_id}")
    print(f"   - State change: {sample_event.old_state} → {sample_event.new_state}")
    print(f"   - Temperature: {sample_event.temperature:.1f}°C")
    print(f"   - Occupancy: {sample_event.occupancy_state}")

    # Test embeddings
    if sample_event.embedding is not None:
        print(f"✅ Embedding generated: {sample_event.embedding.shape}")
    else:
        print("⚠️  No embedding generated")

    print("🎉 Preprocessing pipeline test completed!")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
