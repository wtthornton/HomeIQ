"""
Enhanced Multi-Device Synergy Detector

Extends DeviceSynergyDetector with:
- Sequential pattern detection (A → B → C)
- Simultaneous pattern detection (A + B together)
- Complementary device detection (A enhances B)
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class EnhancedSynergyDetector:
    """
    Enhanced synergy detection with sequential, simultaneous, and complementary patterns.
    
    Wraps DeviceSynergyDetector and adds advanced detection methods.
    """
    
    def __init__(self, base_synergy_detector, data_api_client=None):
        """
        Initialize enhanced synergy detector.
        
        Args:
            base_synergy_detector: Base DeviceSynergyDetector instance
            data_api_client: Data API client for fetching events
        """
        self.base_detector = base_synergy_detector
        self.data_api = data_api_client
        logger.info("EnhancedSynergyDetector initialized")
    
    async def detect_enhanced_synergies(
        self,
        events_df=None,
        window_minutes: int = 30
    ) -> List[Dict]:
        """
        Detect enhanced synergies including sequential, simultaneous, and complementary.
        
        Args:
            events_df: Optional events DataFrame (if None, will fetch)
            window_minutes: Time window for sequential/simultaneous detection
            
        Returns:
            List of enhanced synergy dictionaries
        """
        synergies = []
        
        # Get base synergies
        base_synergies = await self.base_detector.detect_synergies()
        synergies.extend(base_synergies)
        
        # Fetch events if needed
        if events_df is None and self.data_api:
            try:
                from datetime import timezone
                end_time = datetime.now(timezone.utc)
                start_time = end_time - timedelta(days=30)
                events_df = await self.data_api.fetch_events(
                    start_time=start_time,
                    end_time=end_time,
                    limit=50000
                )
            except Exception as e:
                logger.warning(f"Failed to fetch events for enhanced detection: {e}")
                return synergies
        
        if events_df is not None and not events_df.empty:
            # Detect sequential patterns
            sequential = await self._detect_sequential_patterns(events_df, window_minutes)
            synergies.extend(sequential)
            
            # Detect simultaneous patterns
            simultaneous = await self._detect_simultaneous_patterns(events_df, window_minutes // 6)  # 5 minutes
            synergies.extend(simultaneous)
            
            # Detect complementary patterns
            complementary = await self._detect_complementary_patterns(events_df)
            synergies.extend(complementary)
        
        logger.info(f"Enhanced synergy detection: {len(base_synergies)} base + {len(synergies) - len(base_synergies)} enhanced = {len(synergies)} total")
        return synergies
    
    async def _detect_sequential_patterns(
        self,
        events_df,
        window_minutes: int
    ) -> List[Dict]:
        """Detect sequential patterns (A → B → C)."""
        sequential = []
        
        try:
            import pandas as pd
            
            # Sort by time
            if 'time' in events_df.columns:
                events_sorted = events_df.sort_values('time')
            elif 'timestamp' in events_df.columns:
                events_sorted = events_df.sort_values('timestamp')
            else:
                return sequential
            
            # Find sequences
            window = timedelta(minutes=window_minutes)
            sequences = defaultdict(list)
            
            for i, event in events_sorted.iterrows():
                device_id = event.get('entity_id') or event.get('device_id')
                state = str(event.get('state', '')).lower()
                time = pd.to_datetime(event.get('time') or event.get('timestamp'))
                
                if not device_id or state not in ['on', 'open', 'active']:
                    continue
                
                # Look for sequences starting from this device
                sequence_key = (device_id,)
                sequences[sequence_key].append((device_id, time))
                
                # Check for continuation of sequences
                for seq_key, seq_events in list(sequences.items()):
                    if len(seq_events) >= 2:
                        last_time = seq_events[-1][1]
                        if (time - last_time) <= window:
                            # Continue sequence
                            new_key = seq_key + (device_id,)
                            sequences[new_key].append((device_id, time))
            
            # Extract valid sequences (3+ devices)
            for seq_key, seq_events in sequences.items():
                if len(seq_key) >= 3 and len(seq_events) >= 3:
                    # Create synergy
                    device_ids = list(seq_key)
                    sequential.append({
                        'synergy_id': f"sequential_{'_'.join(device_ids[:3])}",
                        'synergy_type': 'sequential_chain',
                        'devices': device_ids,
                        'relationship': f"{device_ids[0]} → {device_ids[1]} → {device_ids[2]}",
                        'confidence': 0.75,
                        'impact_score': 0.7,
                        'complexity': 'medium',
                        'metadata': {
                            'pattern_type': 'sequential',
                            'chain_length': len(device_ids),
                            'occurrences': len(seq_events)
                        }
                    })
        
        except Exception as e:
            logger.error(f"Error detecting sequential patterns: {e}", exc_info=True)
        
        logger.info(f"Detected {len(sequential)} sequential patterns")
        return sequential
    
    async def _detect_simultaneous_patterns(
        self,
        events_df,
        window_seconds: int = 300  # 5 minutes
    ) -> List[Dict]:
        """Detect simultaneous patterns (A + B together)."""
        simultaneous = []
        
        try:
            import pandas as pd
            
            # Sort by time
            if 'time' in events_df.columns:
                events_sorted = events_df.sort_values('time')
            elif 'timestamp' in events_df.columns:
                events_sorted = events_df.sort_values('timestamp')
            else:
                return simultaneous
            
            # Find devices activated together
            window = timedelta(seconds=window_seconds)
            device_pairs = defaultdict(int)
            
            for i, event in events_sorted.iterrows():
                device_id = event.get('entity_id') or event.get('device_id')
                state = str(event.get('state', '')).lower()
                time = pd.to_datetime(event.get('time') or event.get('timestamp'))
                
                if not device_id or state not in ['on', 'open', 'active']:
                    continue
                
                # Find other devices activated within window
                window_end = time + window
                window_events = events_sorted[
                    (events_sorted['time' if 'time' in events_sorted.columns else 'timestamp'] >= time) &
                    (events_sorted['time' if 'time' in events_sorted.columns else 'timestamp'] <= window_end)
                ]
                
                for _, other_event in window_events.iterrows():
                    other_device = other_event.get('entity_id') or other_event.get('device_id')
                    other_state = str(other_event.get('state', '')).lower()
                    
                    if other_device and other_device != device_id and other_state in ['on', 'open', 'active']:
                        pair = tuple(sorted([device_id, other_device]))
                        device_pairs[pair] += 1
            
            # Create synergies for frequent pairs
            for (device1, device2), count in device_pairs.items():
                if count >= 5:  # Minimum 5 occurrences
                    simultaneous.append({
                        'synergy_id': f"simultaneous_{device1}_{device2}",
                        'synergy_type': 'simultaneous_pair',
                        'devices': [device1, device2],
                        'relationship': f"{device1} and {device2} used together",
                        'confidence': min(0.9, 0.6 + (count / 50)),
                        'impact_score': 0.6,
                        'complexity': 'low',
                        'metadata': {
                            'pattern_type': 'simultaneous',
                            'occurrences': count
                        }
                    })
        
        except Exception as e:
            logger.error(f"Error detecting simultaneous patterns: {e}", exc_info=True)
        
        logger.info(f"Detected {len(simultaneous)} simultaneous patterns")
        return simultaneous
    
    async def _detect_complementary_patterns(self, events_df) -> List[Dict]:
        """Detect complementary patterns (A enhances B)."""
        complementary = []
        
        # Examples: temperature sensor + fan, motion sensor + light
        # These are detected by the base synergy detector, so we can enhance them here
        
        # For now, return empty - base detector already handles this
        # This method can be extended with domain-specific logic
        
        return complementary

