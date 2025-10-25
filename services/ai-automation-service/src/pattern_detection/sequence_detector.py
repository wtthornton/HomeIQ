"""
Sequence Pattern Detector

Detects multi-step behavior patterns using ML clustering and pandas optimizations.
Example: "Coffee maker → Kitchen light → Music" sequences.

Story AI5.3: Converted to incremental processing with aggregate storage.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, timezone
from collections import defaultdict, Counter

from .ml_pattern_detector import MLPatternDetector

logger = logging.getLogger(__name__)


class SequenceDetector(MLPatternDetector):
    """
    Detects multi-step behavior patterns in device sequences.
    
    Uses pandas rolling windows and ML clustering to identify:
    - Device activation sequences
    - Time-based patterns in sequences
    - Sequence frequency and confidence
    - Similar sequence clustering
    """
    
    def __init__(
        self,
        window_minutes: int = 30,
        min_sequence_length: int = 2,
        max_sequence_length: int = 5,
        min_sequence_occurrences: int = 3,
        sequence_gap_seconds: int = 300,  # 5 minutes max gap between sequence steps
        aggregate_client=None,
        **kwargs
    ):
        """
        Initialize sequence detector.
        
        Args:
            window_minutes: Time window for sequence detection
            min_sequence_length: Minimum devices in sequence
            max_sequence_length: Maximum devices in sequence
            min_sequence_occurrences: Minimum occurrences for valid sequence
            sequence_gap_seconds: Maximum gap between sequence steps
            aggregate_client: PatternAggregateClient for storing daily aggregates (Story AI5.3)
            **kwargs: Additional MLPatternDetector parameters
        """
        super().__init__(**kwargs)
        self.window_minutes = window_minutes
        self.min_sequence_length = min_sequence_length
        self.max_sequence_length = max_sequence_length
        self.min_sequence_occurrences = min_sequence_occurrences
        self.sequence_gap_seconds = sequence_gap_seconds
        self.aggregate_client = aggregate_client
        
        logger.info(f"SequenceDetector initialized: window={window_minutes}min, min_length={min_sequence_length}")
    
    def detect_patterns(self, events_df: pd.DataFrame) -> List[Dict]:
        """
        Detect sequence patterns in events.
        
        Args:
            events_df: Events DataFrame with time, entity_id, state columns
            
        Returns:
            List of sequence pattern dictionaries
        """
        start_time = datetime.utcnow()
        
        if not self._validate_events_dataframe(events_df):
            return []
        
        # Optimize DataFrame for processing
        events_df = self._optimize_dataframe(events_df)
        
        # Filter for state changes (on/off transitions)
        state_changes = self._filter_state_changes(events_df)
        if state_changes.empty:
            logger.info("No state changes found for sequence detection")
            return []
        
        # Detect sequences using rolling windows
        sequences = self._detect_sequences(state_changes)
        if not sequences:
            logger.info("No sequences detected")
            return []
        
        # Cluster similar sequences using ML
        if self.enable_ml and len(sequences) > 2:
            sequences = self._cluster_sequences(sequences)
        
        # Convert sequences to patterns
        patterns = self._sequences_to_patterns(sequences)
        
        # Update statistics
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        self.detection_stats['total_patterns'] += len(patterns)
        self.detection_stats['processing_time'] += processing_time
        
        logger.info(f"Detected {len(patterns)} sequence patterns in {processing_time:.2f}s")
        
        # Story AI5.3: Store daily aggregates to InfluxDB
        if self.aggregate_client and patterns:
            self._store_daily_aggregates(patterns, events_df)
        
        return patterns
    
    def _store_daily_aggregates(self, patterns: List[Dict], events_df: pd.DataFrame) -> None:
        """
        Store daily aggregates to InfluxDB.
        
        Story AI5.3: Incremental pattern processing with aggregate storage.
        
        Args:
            patterns: List of detected patterns
            events_df: Original events DataFrame
        """
        try:
            # Get date from events
            if events_df.empty or 'time' not in events_df.columns:
                logger.warning("Cannot determine date from events for aggregate storage")
                return
            
            # Use the date of the first event (assuming 24h window)
            date = pd.to_datetime(events_df['time'].min()).date()
            date_str = date.strftime("%Y-%m-%d")
            
            logger.info(f"Storing daily aggregates for {date_str}")
            
            for pattern in patterns:
                # Get sequence signature and metadata
                sequence_signature = pattern.get('sequence_signature', '')
                sequence_length = pattern.get('metadata', {}).get('sequence_length', 0)
                duration_seconds = pattern.get('metadata', {}).get('duration_seconds', 0)
                avg_gap_seconds = pattern.get('metadata', {}).get('avg_gap_seconds', 0)
                
                # Extract first device as entity_id
                devices = pattern.get('devices', [])
                entity_id = devices[0] if devices else 'unknown'
                domain = entity_id.split('.')[0] if '.' in entity_id else 'unknown'
                
                # Calculate metrics
                occurrences = pattern.get('occurrences', 0)
                confidence = pattern.get('confidence', 0.0)
                
                # Store aggregate
                try:
                    self.aggregate_client.write_sequence_daily(
                        date=date_str,
                        entity_id=sequence_signature or entity_id,
                        domain=domain,
                        sequence_length=sequence_length,
                        occurrences=occurrences,
                        confidence=confidence,
                        duration_seconds=duration_seconds,
                        avg_gap_seconds=avg_gap_seconds,
                        devices=devices
                    )
                except Exception as e:
                    logger.error(f"Failed to store aggregate for {entity_id}: {e}", exc_info=True)
            
            logger.info(f"✅ Stored {len(patterns)} daily aggregates to InfluxDB")
            
        except Exception as e:
            logger.error(f"Error storing daily aggregates: {e}", exc_info=True)
    
    def _filter_state_changes(self, events_df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter events to only include state changes (on/off transitions).
        
        Args:
            events_df: Events DataFrame
            
        Returns:
            DataFrame with only state change events
        """
        # Group by entity and find state changes
        state_changes = []
        
        for entity_id, entity_events in events_df.groupby('entity_id'):
            entity_events = entity_events.sort_values('time')
            
            # Find state transitions
            state_transitions = entity_events['state'].ne(entity_events['state'].shift())
            state_changes_events = entity_events[state_transitions].copy()
            
            if not state_changes_events.empty:
                state_changes_events['entity_id'] = entity_id
                state_changes.append(state_changes_events)
        
        if state_changes:
            return pd.concat(state_changes, ignore_index=True)
        else:
            return pd.DataFrame()
    
    def _detect_sequences(self, events_df: pd.DataFrame) -> List[Dict]:
        """
        Detect sequences using rolling window approach.
        
        Args:
            events_df: State change events DataFrame
            
        Returns:
            List of detected sequences
        """
        sequences = []
        window_size = pd.Timedelta(minutes=self.window_minutes)
        
        # Sort by time for rolling window processing
        events_sorted = events_df.sort_values('time').reset_index(drop=True)
        
        # Use rolling window to find sequences
        for i in range(len(events_sorted)):
            window_start = events_sorted.iloc[i]['time']
            window_end = window_start + window_size
            
            # Get events in window
            window_events = events_sorted[
                (events_sorted['time'] >= window_start) & 
                (events_sorted['time'] <= window_end)
            ]
            
            # Extract sequences from window
            window_sequences = self._extract_sequences_from_window(window_events)
            sequences.extend(window_sequences)
        
        # Deduplicate and count occurrences
        return self._deduplicate_sequences(sequences)
    
    def _extract_sequences_from_window(self, window_events: pd.DataFrame) -> List[Dict]:
        """
        Extract sequences from a time window.
        
        Args:
            window_events: Events in time window
            
        Returns:
            List of sequences found in window
        """
        sequences = []
        
        if len(window_events) < self.min_sequence_length:
            return sequences
        
        # Group by time to find simultaneous events
        time_groups = window_events.groupby('time')
        
        # Build sequences by following time progression
        current_sequence = []
        last_time = None
        
        for time, time_events in time_groups:
            # Check if gap is too large (break sequence)
            if last_time is not None:
                gap = (time - last_time).total_seconds()
                if gap > self.sequence_gap_seconds:
                    # Save current sequence if valid
                    if len(current_sequence) >= self.min_sequence_length:
                        sequences.append(self._create_sequence_dict(current_sequence))
                    current_sequence = []
            
            # Add events to current sequence
            for _, event in time_events.iterrows():
                if len(current_sequence) < self.max_sequence_length:
                    current_sequence.append({
                        'entity_id': event['entity_id'],
                        'state': event['state'],
                        'time': event['time'],
                        'area': event.get('area', 'unknown')
                    })
            
            last_time = time
        
        # Save final sequence if valid
        if len(current_sequence) >= self.min_sequence_length:
            sequences.append(self._create_sequence_dict(current_sequence))
        
        return sequences
    
    def _create_sequence_dict(self, sequence_events: List[Dict]) -> Dict:
        """
        Create sequence dictionary from events.
        
        Args:
            sequence_events: List of events in sequence
            
        Returns:
            Sequence dictionary
        """
        # Extract sequence information
        devices = [event['entity_id'] for event in sequence_events]
        states = [event['state'] for event in sequence_events]
        times = [event['time'] for event in sequence_events]
        areas = [event['area'] for event in sequence_events]
        
        # Calculate sequence metrics
        duration = (times[-1] - times[0]).total_seconds()
        avg_gap = np.mean([(times[i+1] - times[i]).total_seconds() for i in range(len(times)-1)])
        
        # Create sequence signature for deduplication
        sequence_signature = tuple(zip(devices, states))
        
        return {
            'signature': sequence_signature,
            'devices': devices,
            'states': states,
            'times': times,
            'areas': areas,
            'duration': duration,
            'avg_gap': avg_gap,
            'length': len(sequence_events),
            'first_time': times[0],
            'last_time': times[-1]
        }
    
    def _deduplicate_sequences(self, sequences: List[Dict]) -> List[Dict]:
        """
        Deduplicate sequences and count occurrences.
        
        Args:
            sequences: List of sequence dictionaries
            
        Returns:
            Deduplicated sequences with occurrence counts
        """
        # Count sequence occurrences
        sequence_counts = Counter(seq['signature'] for seq in sequences)
        
        # Keep only sequences with enough occurrences
        valid_sequences = []
        for seq in sequences:
            signature = seq['signature']
            occurrences = sequence_counts[signature]
            
            if occurrences >= self.min_sequence_occurrences:
                seq['occurrences'] = occurrences
                valid_sequences.append(seq)
        
        # Remove duplicates
        seen_signatures = set()
        unique_sequences = []
        
        for seq in valid_sequences:
            signature = seq['signature']
            if signature not in seen_signatures:
                seen_signatures.add(signature)
                unique_sequences.append(seq)
        
        return unique_sequences
    
    def _cluster_sequences(self, sequences: List[Dict]) -> List[Dict]:
        """
        Cluster similar sequences using ML.
        
        Args:
            sequences: List of sequence dictionaries
            
        Returns:
            Clustered sequences with cluster information
        """
        if len(sequences) < 3:
            return sequences
        
        try:
            # Extract features for clustering
            features = self._extract_sequence_features(sequences)
            
            # Cluster sequences
            sequences = self._cluster_patterns(sequences, features)
            
            logger.info(f"Clustered {len(sequences)} sequences")
            
        except Exception as e:
            logger.warning(f"Sequence clustering failed: {e}")
        
        return sequences
    
    def _extract_sequence_features(self, sequences: List[Dict]) -> np.ndarray:
        """
        Extract features for sequence clustering.
        
        Args:
            sequences: List of sequence dictionaries
            
        Returns:
            Feature matrix for clustering
        """
        features = []
        
        for seq in sequences:
            feature_vector = [
                seq['length'],  # Sequence length
                seq['duration'],  # Total duration
                seq['avg_gap'],  # Average gap between steps
                len(set(seq['devices'])),  # Number of unique devices
                len(set(seq['areas'])),  # Number of unique areas
                seq['first_time'].hour,  # Hour of day
                seq['first_time'].dayofweek,  # Day of week
                seq['occurrences']  # Number of occurrences
            ]
            features.append(feature_vector)
        
        return np.array(features)
    
    def _sequences_to_patterns(self, sequences: List[Dict]) -> List[Dict]:
        """
        Convert sequences to pattern dictionaries.
        
        Args:
            sequences: List of sequence dictionaries
            
        Returns:
            List of pattern dictionaries
        """
        patterns = []
        
        for seq in sequences:
            # Calculate confidence
            confidence = self._calculate_sequence_confidence(seq)
            
            if confidence < self.min_confidence:
                continue
            
            # Create pattern dictionary
            pattern = self._create_pattern_dict(
                pattern_type='sequence',
                pattern_id=self._generate_pattern_id('seq'),
                confidence=confidence,
                occurrences=seq['occurrences'],
                devices=seq['devices'],
                metadata={
                    'sequence_length': seq['length'],
                    'duration_seconds': seq['duration'],
                    'avg_gap_seconds': seq['avg_gap'],
                    'areas': list(set(seq['areas'])),
                    'first_occurrence': seq['first_time'].isoformat(),
                    'last_occurrence': seq['last_time'].isoformat(),
                    'sequence_states': seq['states']
                },
                sequence_signature=seq['signature']
            )
            
            # Add ML-specific fields if available
            if 'cluster_id' in seq:
                pattern['cluster_id'] = seq['cluster_id']
            if 'ml_confidence' in seq:
                pattern['ml_confidence'] = seq['ml_confidence']
            
            patterns.append(pattern)
        
        # Sort by confidence and limit results
        patterns.sort(key=lambda x: x['confidence'], reverse=True)
        return patterns[:self.max_patterns]
    
    def _calculate_sequence_confidence(self, sequence: Dict) -> float:
        """
        Calculate confidence for sequence pattern.
        
        Args:
            sequence: Sequence dictionary
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Base confidence from occurrences
        occurrences = sequence['occurrences']
        base_confidence = min(occurrences / 10.0, 1.0)  # Max at 10 occurrences
        
        # Length bonus (longer sequences are more significant)
        length_bonus = min(sequence['length'] / 5.0, 0.3)  # Max 30% bonus
        
        # Consistency bonus (consistent timing)
        avg_gap = sequence['avg_gap']
        consistency_bonus = 0.0
        if avg_gap > 0:
            # More consistent timing = higher confidence
            consistency_bonus = min(1.0 / (avg_gap / 60.0 + 1), 0.2)  # Max 20% bonus
        
        # Device diversity bonus
        unique_devices = len(set(sequence['devices']))
        diversity_bonus = min(unique_devices / 5.0, 0.2)  # Max 20% bonus
        
        total_confidence = base_confidence + length_bonus + consistency_bonus + diversity_bonus
        
        return min(total_confidence, 1.0)
