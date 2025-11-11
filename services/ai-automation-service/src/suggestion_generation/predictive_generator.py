"""
Predictive Automation Generator

Detects automation opportunities proactively:
- Repetitive manual actions
- Energy waste
- Convenience opportunities
- Weather-responsive suggestions
"""

import logging
import pandas as pd
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)


class PredictiveAutomationGenerator:
    """
    Generates predictive automation suggestions based on:
    - Repetitive actions
    - Energy waste patterns
    - Convenience opportunities
    - Weather-responsive needs
    """
    
    def __init__(self, min_repetitions: int = 5, min_energy_waste_hours: float = 2.0):
        """
        Initialize predictive automation generator.
        
        Args:
            min_repetitions: Minimum repetitions to suggest automation
            min_energy_waste_hours: Minimum hours of waste to suggest optimization
        """
        self.min_repetitions = min_repetitions
        self.min_energy_waste_hours = min_energy_waste_hours
        logger.info("PredictiveAutomationGenerator initialized")
    
    def generate_predictive_suggestions(
        self,
        events_df: pd.DataFrame,
        devices: Optional[List[Dict]] = None
    ) -> List[Dict]:
        """
        Generate predictive automation suggestions.
        
        Args:
            events_df: Events DataFrame
            devices: Optional list of devices
            
        Returns:
            List of predictive suggestion dictionaries
        """
        suggestions = []
        
        if events_df.empty:
            return suggestions
        
        # 1. Detect repetitive manual actions
        repetitive = self._detect_repetitive_actions(events_df)
        suggestions.extend(self._suggest_automations_for_repetitive(repetitive))
        
        # 2. Detect energy waste
        energy_waste = self._detect_energy_waste(events_df)
        suggestions.extend(self._suggest_energy_optimizations(energy_waste))
        
        # 3. Detect convenience opportunities
        opportunities = self._detect_convenience_opportunities(events_df, devices)
        suggestions.extend(self._suggest_convenience_automations(opportunities))
        
        logger.info(f"Generated {len(suggestions)} predictive suggestions")
        return suggestions
    
    def _detect_repetitive_actions(self, events_df: pd.DataFrame) -> List[Dict]:
        """Detect repetitive manual actions that could be automated."""
        repetitive = []
        
        # Group by device and action
        device_actions = defaultdict(list)
        for _, event in events_df.iterrows():
            device_id = event.get('entity_id') or event.get('device_id')
            state = event.get('state', '')
            time = event.get('time') or event.get('timestamp')
            
            if device_id and state and time:
                key = (device_id, state)
                device_actions[key].append(time)
        
        # Find patterns that repeat frequently
        for (device_id, state), times in device_actions.items():
            if len(times) >= self.min_repetitions:
                # Check if times are clustered (same time pattern)
                times_sorted = sorted([pd.to_datetime(t) for t in times])
                time_diffs = [(times_sorted[i+1] - times_sorted[i]).total_seconds() 
                             for i in range(len(times_sorted)-1)]
                
                # If most actions happen within same hour window, it's repetitive
                hour_counts = Counter([pd.to_datetime(t).hour for t in times])
                most_common_hour, count = hour_counts.most_common(1)[0]
                
                if count >= self.min_repetitions:
                    repetitive.append({
                        'device_id': device_id,
                        'state': state,
                        'occurrences': len(times),
                        'most_common_hour': most_common_hour,
                        'pattern_type': 'repetitive_manual'
                    })
        
        return repetitive
    
    def _suggest_automations_for_repetitive(self, repetitive: List[Dict]) -> List[Dict]:
        """Generate automation suggestions for repetitive actions."""
        suggestions = []
        
        for action in repetitive:
            device_id = action['device_id']
            hour = action['most_common_hour']
            occurrences = action['occurrences']
            
            suggestions.append({
                'type': 'repetitive_action',
                'title': f"Automate {device_id} at {hour:02d}:00",
                'description': f"You manually turn on {device_id} {occurrences} times around {hour:02d}:00. "
                              f"Consider automating this action.",
                'confidence': 0.85,
                'priority': 'high',
                'device_id': device_id,
                'metadata': {
                    'occurrences': occurrences,
                    'suggested_time': f"{hour:02d}:00",
                    'pattern_type': 'repetitive_manual'
                }
            })
        
        return suggestions
    
    def _detect_energy_waste(self, events_df: pd.DataFrame) -> List[Dict]:
        """Detect energy waste patterns (devices left on too long)."""
        waste = []
        
        # Find devices that stay on for extended periods
        device_states = defaultdict(lambda: {'on_time': None, 'total_on_hours': 0.0})
        
        sorted_events = events_df.sort_values('time' if 'time' in events_df.columns else 'timestamp')
        
        for _, event in sorted_events.iterrows():
            device_id = event.get('entity_id') or event.get('device_id')
            state = str(event.get('state', '')).lower()
            time = pd.to_datetime(event.get('time') or event.get('timestamp'))
            
            if not device_id:
                continue
            
            if state in ['on', 'open', 'active']:
                device_states[device_id]['on_time'] = time
            elif state in ['off', 'closed', 'inactive'] and device_states[device_id]['on_time']:
                on_time = device_states[device_id]['on_time']
                hours = (time - on_time).total_seconds() / 3600.0
                if hours >= self.min_energy_waste_hours:
                    device_states[device_id]['total_on_hours'] += hours
                device_states[device_id]['on_time'] = None
        
        # Check for devices with significant waste
        for device_id, state_info in device_states.items():
            if state_info['total_on_hours'] >= self.min_energy_waste_hours:
                waste.append({
                    'device_id': device_id,
                    'waste_hours': state_info['total_on_hours'],
                    'pattern_type': 'energy_waste'
                })
        
        return waste
    
    def _suggest_energy_optimizations(self, waste: List[Dict]) -> List[Dict]:
        """Generate energy optimization suggestions."""
        suggestions = []
        
        for item in waste:
            device_id = item['device_id']
            waste_hours = item['waste_hours']
            
            suggestions.append({
                'type': 'energy_optimization',
                'title': f"Auto-off for {device_id}",
                'description': f"{device_id} was left on for {waste_hours:.1f} hours. "
                              f"Consider adding an auto-off timer or motion-based control.",
                'confidence': 0.90,
                'priority': 'medium',
                'device_id': device_id,
                'metadata': {
                    'waste_hours': waste_hours,
                    'pattern_type': 'energy_waste'
                }
            })
        
        return suggestions
    
    def _detect_convenience_opportunities(
        self,
        events_df: pd.DataFrame,
        devices: Optional[List[Dict]]
    ) -> List[Dict]:
        """Detect convenience opportunities (multiple devices used together)."""
        opportunities = []
        
        # Find devices used together frequently
        if len(events_df) < 10:
            return opportunities
        
        # Group events by time window (within 5 minutes)
        time_window = timedelta(minutes=5)
        device_groups = defaultdict(set)
        
        sorted_events = events_df.sort_values('time' if 'time' in events_df.columns else 'timestamp')
        
        for i, event in sorted_events.iterrows():
            device_id = event.get('entity_id') or event.get('device_id')
            time = pd.to_datetime(event.get('time') or event.get('timestamp'))
            state = str(event.get('state', '')).lower()
            
            if not device_id or state not in ['on', 'open', 'active']:
                continue
            
            # Find other devices activated within time window
            window_end = time + time_window
            window_events = sorted_events[
                (sorted_events['time' if 'time' in sorted_events.columns else 'timestamp'] >= time) &
                (sorted_events['time' if 'time' in sorted_events.columns else 'timestamp'] <= window_end)
            ]
            
            for _, other_event in window_events.iterrows():
                other_device = other_event.get('entity_id') or other_event.get('device_id')
                other_state = str(other_event.get('state', '')).lower()
                
                if other_device and other_device != device_id and other_state in ['on', 'open', 'active']:
                    pair = tuple(sorted([device_id, other_device]))
                    device_groups[pair].add(time)
        
        # Find pairs that occur together frequently
        for (device1, device2), times in device_groups.items():
            if len(times) >= self.min_repetitions:
                opportunities.append({
                    'device1': device1,
                    'device2': device2,
                    'occurrences': len(times),
                    'pattern_type': 'convenience_opportunity'
                })
        
        return opportunities
    
    def _suggest_convenience_automations(self, opportunities: List[Dict]) -> List[Dict]:
        """Generate convenience automation suggestions."""
        suggestions = []
        
        for opp in opportunities:
            device1 = opp['device1']
            device2 = opp['device2']
            occurrences = opp['occurrences']
            
            suggestions.append({
                'type': 'convenience_opportunity',
                'title': f"Automate {device1} and {device2} together",
                'description': f"{device1} and {device2} are used together {occurrences} times. "
                              f"Consider creating a scene or automation to activate both together.",
                'confidence': 0.80,
                'priority': 'medium',
                'device1': device1,
                'device2': device2,
                'metadata': {
                    'occurrences': occurrences,
                    'pattern_type': 'convenience_opportunity'
                }
            })
        
        return suggestions







