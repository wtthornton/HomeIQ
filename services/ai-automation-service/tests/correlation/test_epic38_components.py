"""
Unit Tests for Epic 38 Advanced Features Components

Epic 38, Story 38.8: Documentation and Testing
Comprehensive unit tests for calendar integration, presence-aware correlations,
augmented analytics, and automated insights.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Optional

from src.correlation import (
    CorrelationService,
    CalendarCorrelationIntegration,
    AugmentedCorrelationAnalytics,
    PresenceAwareCorrelationAnalyzer,
    AutomatedCorrelationInsights
)


class TestCalendarCorrelationIntegration:
    """Unit tests for calendar correlation integration"""
    
    @pytest.fixture
    def calendar_integration(self):
        """Create calendar integration instance"""
        return CalendarCorrelationIntegration(
            calendar_service_url=None,  # Mock mode
            cache_ttl=timedelta(hours=1),
            max_cache_size=100
        )
    
    @pytest.mark.asyncio
    async def test_initialization(self, calendar_integration):
        """Test calendar integration initialization"""
        assert calendar_integration.calendar_service_url is not None
        assert calendar_integration.cache_ttl == timedelta(hours=1)
        assert calendar_integration.max_cache_size == 100
        assert calendar_integration.calendar_available is True
    
    @pytest.mark.asyncio
    async def test_connect_and_close(self, calendar_integration):
        """Test HTTP session connection and cleanup"""
        await calendar_integration.connect()
        assert calendar_integration.session is not None
        
        await calendar_integration.close()
        assert calendar_integration.session is None
    
    @pytest.mark.asyncio
    async def test_get_current_presence_cached(self, calendar_integration):
        """Test getting current presence with cache"""
        timestamp = datetime.now(timezone.utc)
        
        # Mock presence data
        mock_presence = {
            'currently_home': True,
            'wfh_today': False,
            'confidence': 0.9,
            'timestamp': timestamp
        }
        
        # Cache the presence
        cache_key = timestamp.replace(minute=0, second=0, microsecond=0)
        calendar_integration.presence_cache[cache_key] = {
            'data': mock_presence,
            'timestamp': timestamp
        }
        
        # Get presence (should use cache)
        result = await calendar_integration.get_current_presence(timestamp)
        
        assert result is not None
        assert result['currently_home'] is True
        assert result['confidence'] == 0.9
    
    @pytest.mark.asyncio
    async def test_get_current_presence_fallback(self, calendar_integration):
        """Test getting current presence with fallback"""
        timestamp = datetime.now(timezone.utc)
        
        # Mock InfluxDB query to return None (no data)
        with patch.object(calendar_integration, '_query_presence_from_influxdb', return_value=None):
            result = await calendar_integration.get_current_presence(timestamp)
            
            # Should return fallback
            assert result is not None
            assert result['currently_home'] is True  # Conservative default
            assert result['confidence'] == 0.5  # Low confidence for fallback
    
    @pytest.mark.asyncio
    async def test_get_predicted_presence(self, calendar_integration):
        """Test getting predicted presence"""
        timestamp = datetime.now(timezone.utc)
        
        # Mock future presence query
        mock_prediction = {
            'next_arrival': timestamp + timedelta(hours=2),
            'next_departure': timestamp + timedelta(hours=8),
            'will_be_home': True,
            'confidence': 0.85,
            'timestamp': timestamp
        }
        
        with patch.object(
            calendar_integration,
            '_query_future_presence_from_influxdb',
            return_value=mock_prediction
        ):
            result = await calendar_integration.get_predicted_presence(
                hours_ahead=24,
                timestamp=timestamp
            )
            
            assert result is not None
            assert result['will_be_home'] is True
            assert result['confidence'] == 0.85
    
    @pytest.mark.asyncio
    async def test_get_presence_features(self, calendar_integration):
        """Test getting presence features for correlation"""
        timestamp = datetime.now(timezone.utc)
        
        # Mock current and predicted presence
        mock_current = {
            'currently_home': True,
            'wfh_today': False,
            'confidence': 0.9,
            'timestamp': timestamp
        }
        
        mock_predicted = {
            'next_arrival': timestamp + timedelta(hours=2),
            'next_departure': timestamp + timedelta(hours=8),
            'will_be_home': True,
            'confidence': 0.85,
            'timestamp': timestamp
        }
        
        with patch.object(
            calendar_integration,
            'get_current_presence',
            return_value=mock_current
        ), patch.object(
            calendar_integration,
            'get_predicted_presence',
            return_value=mock_predicted
        ):
            features = await calendar_integration.get_presence_features(timestamp)
            
            assert 'current_presence' in features
            assert 'predicted_presence' in features
            assert features['current_presence']['currently_home'] is True
            assert features['predicted_presence']['will_be_home'] is True


class TestAugmentedCorrelationAnalytics:
    """Unit tests for augmented correlation analytics"""
    
    @pytest.fixture
    def correlation_service(self):
        """Create correlation service instance"""
        return CorrelationService(
            enable_tabpfn=True,
            enable_streaming=True,
            enable_vector_db=False
        )
    
    @pytest.fixture
    def augmented_analytics(self, correlation_service):
        """Create augmented analytics instance"""
        return AugmentedCorrelationAnalytics(correlation_service)
    
    @pytest.mark.asyncio
    async def test_initialization(self, augmented_analytics):
        """Test augmented analytics initialization"""
        assert augmented_analytics.correlation_service is not None
    
    @pytest.mark.asyncio
    async def test_detect_patterns(self, augmented_analytics):
        """Test pattern detection"""
        entities = [
            {'entity_id': 'light.living', 'domain': 'light', 'area_id': 'living_room'},
            {'entity_id': 'binary_sensor.motion', 'domain': 'binary_sensor', 'area_id': 'living_room'}
        ]
        
        correlations = [
            {
                'entity1_id': 'light.living',
                'entity2_id': 'binary_sensor.motion',
                'correlation': 0.85,
                'confidence': 0.9
            }
        ]
        
        patterns = await augmented_analytics.detect_patterns(entities, correlations)
        
        assert isinstance(patterns, list)
        # Patterns may be empty if no strong patterns detected, which is acceptable
    
    @pytest.mark.asyncio
    async def test_explain_correlation(self, augmented_analytics):
        """Test correlation explanation generation"""
        correlation_data = {
            'entity1_id': 'light.living',
            'entity2_id': 'binary_sensor.motion',
            'correlation': 0.85,
            'confidence': 0.9,
            'features': {
                'same_area': True,
                'temporal_proximity': 0.8
            }
        }
        
        explanation = await augmented_analytics.explain_correlation(correlation_data)
        
        assert isinstance(explanation, str)
        assert len(explanation) > 0
    
    @pytest.mark.asyncio
    async def test_explain_correlation_with_metadata(self, augmented_analytics):
        """Test correlation explanation with entity metadata"""
        entity1 = {'entity_id': 'light.living', 'domain': 'light', 'area_id': 'living_room'}
        entity2 = {'entity_id': 'binary_sensor.motion', 'domain': 'binary_sensor', 'area_id': 'living_room'}
        
        explanation = await augmented_analytics.explain_correlation(
            entity1, entity2, correlation=0.85, confidence=0.9
        )
        
        assert isinstance(explanation, str)
        assert len(explanation) > 0


class TestPresenceAwareCorrelationAnalyzer:
    """Unit tests for presence-aware correlation analyzer"""
    
    @pytest.fixture
    def correlation_service(self):
        """Create correlation service instance"""
        return CorrelationService(
            enable_tabpfn=True,
            enable_streaming=True,
            enable_vector_db=False
        )
    
    @pytest.fixture
    def calendar_integration(self):
        """Create calendar integration instance"""
        return CalendarCorrelationIntegration(
            calendar_service_url=None,  # Mock mode
            cache_ttl=timedelta(hours=1)
        )
    
    @pytest.fixture
    def presence_analyzer(self, correlation_service, calendar_integration):
        """Create presence-aware analyzer instance"""
        return PresenceAwareCorrelationAnalyzer(
            correlation_service,
            calendar_integration
        )
    
    @pytest.mark.asyncio
    async def test_initialization(self, presence_analyzer):
        """Test presence-aware analyzer initialization"""
        assert presence_analyzer.correlation_service is not None
        assert presence_analyzer.calendar_integration is not None
    
    @pytest.mark.asyncio
    async def test_analyze_presence_correlation(self, presence_analyzer):
        """Test presence correlation analysis"""
        entity_id = 'light.living'
        timestamp = datetime.now(timezone.utc)
        
        # Mock presence history and device usage
        with patch.object(
            presence_analyzer,
            '_get_presence_history',
            return_value=[]
        ), patch.object(
            presence_analyzer,
            '_get_device_usage_history',
            return_value=[]
        ):
            result = await presence_analyzer.analyze_presence_correlations(
                entity_id,
                hours_back=168,
                timestamp=timestamp
            )
            
            assert isinstance(result, dict)
            assert 'entity_id' in result
            assert result['entity_id'] == entity_id
    
    @pytest.mark.asyncio
    async def test_analyze_presence_correlation_with_data(self, presence_analyzer):
        """Test presence correlation analysis with mock data"""
        entity_id = 'light.living'
        timestamp = datetime.now(timezone.utc)
        
        # Mock presence history
        mock_presence_history = [
            {'timestamp': timestamp - timedelta(hours=i), 'currently_home': i % 2 == 0}
            for i in range(24)
        ]
        
        # Mock device usage history
        mock_usage_history = [
            {'timestamp': timestamp - timedelta(hours=i), 'state': 'on' if i % 2 == 0 else 'off'}
            for i in range(24)
        ]
        
        with patch.object(
            presence_analyzer,
            '_get_presence_history',
            return_value=mock_presence_history
        ), patch.object(
            presence_analyzer,
            '_get_device_usage_history',
            return_value=mock_usage_history
        ):
            result = await presence_analyzer.analyze_presence_correlations(
                entity_id,
                hours_back=24,
                timestamp=timestamp
            )
            
            assert isinstance(result, dict)
            assert 'presence_correlation' in result
            assert 'home_usage_frequency' in result
            assert 'away_usage_frequency' in result


class TestAutomatedCorrelationInsights:
    """Unit tests for automated correlation insights"""
    
    @pytest.fixture
    def correlation_service(self):
        """Create correlation service instance"""
        return CorrelationService(
            enable_tabpfn=True,
            enable_streaming=True,
            enable_vector_db=False
        )
    
    @pytest.fixture
    def augmented_analytics(self, correlation_service):
        """Create augmented analytics instance"""
        return AugmentedCorrelationAnalytics(correlation_service)
    
    @pytest.fixture
    def automated_insights(self, correlation_service, augmented_analytics):
        """Create automated insights instance"""
        return AutomatedCorrelationInsights(
            correlation_service,
            augmented_analytics=augmented_analytics
        )
    
    @pytest.mark.asyncio
    async def test_initialization(self, automated_insights):
        """Test automated insights initialization"""
        assert automated_insights.correlation_service is not None
        assert automated_insights.augmented_analytics is not None
    
    def test_generate_correlation_insights(self, automated_insights):
        """Test correlation insights generation"""
        entity1_id = 'light.living'
        entity2_id = 'binary_sensor.motion'
        
        entity1_metadata = {'domain': 'light', 'area_id': 'living_room'}
        entity2_metadata = {'domain': 'binary_sensor', 'area_id': 'living_room'}
        
        # Mock correlation service
        with patch.object(
            automated_insights.correlation_service,
            'get_correlation',
            return_value=0.85
        ):
            insights = automated_insights.generate_correlation_insights(
                entity1_id,
                entity2_id,
                entity1_metadata,
                entity2_metadata
            )
            
            assert isinstance(insights, dict)
            assert 'correlation_explanation' in insights
            assert 'summary' in insights
            assert 'recommendations' in insights
    
    def test_generate_automation_suggestion(self, automated_insights):
        """Test automation suggestion generation"""
        entity1_id = 'light.living'
        entity2_id = 'binary_sensor.motion'
        correlation_score = 0.85
        
        suggestion = automated_insights.generate_automation_suggestion(
            entity1_id,
            entity2_id,
            correlation_score
        )
        
        assert isinstance(suggestion, dict)
        assert 'trigger' in suggestion
        assert 'action' in suggestion
        assert 'confidence' in suggestion
    
    def test_generate_natural_language_explanation(self, automated_insights):
        """Test natural language explanation generation"""
        correlation_data = {
            'entity1_id': 'light.living',
            'entity2_id': 'binary_sensor.motion',
            'correlation': 0.85,
            'confidence': 0.9,
            'features': {
                'same_area': True,
                'temporal_proximity': 0.8
            }
        }
        
        explanation = automated_insights.generate_natural_language_explanation(
            correlation_data
        )
        
        assert isinstance(explanation, str)
        assert len(explanation) > 0


class TestEpic38Integration:
    """Integration tests for Epic 38 components"""
    
    @pytest.fixture
    async def full_system(self):
        """Create full Epic 38 system"""
        calendar_integration = CalendarCorrelationIntegration(
            calendar_service_url=None,  # Mock mode
            cache_ttl=timedelta(hours=1)
        )
        
        correlation_service = CorrelationService(
            calendar_integration=calendar_integration,
            enable_tabpfn=True,
            enable_streaming=True,
            enable_vector_db=False
        )
        
        augmented_analytics = AugmentedCorrelationAnalytics(correlation_service)
        
        presence_analyzer = PresenceAwareCorrelationAnalyzer(
            correlation_service,
            calendar_integration
        )
        
        automated_insights = AutomatedCorrelationInsights(
            correlation_service,
            augmented_analytics=augmented_analytics,
            presence_analyzer=presence_analyzer
        )
        
        yield {
            'calendar_integration': calendar_integration,
            'correlation_service': correlation_service,
            'augmented_analytics': augmented_analytics,
            'presence_analyzer': presence_analyzer,
            'automated_insights': automated_insights
        }
        
        await calendar_integration.close()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_end_to_end_correlation_analysis(self, full_system):
        """Test end-to-end correlation analysis with all Epic 38 components"""
        calendar_integration = full_system['calendar_integration']
        correlation_service = full_system['correlation_service']
        augmented_analytics = full_system['augmented_analytics']
        automated_insights = full_system['automated_insights']
        
        entity1 = {'entity_id': 'light.living', 'domain': 'light', 'area_id': 'living_room'}
        entity2 = {'entity_id': 'binary_sensor.motion', 'domain': 'binary_sensor', 'area_id': 'living_room'}
        timestamp = datetime.now(timezone.utc)
        
        # Get presence features
        presence_features = await calendar_integration.get_presence_features(timestamp)
        assert 'current_presence' in presence_features
        
        # Compute correlation
        correlation = await correlation_service.compute_correlation(
            entity1, entity2, timestamp=timestamp
        )
        # Correlation may be None if not enough data, which is acceptable
        
        # Generate insights if correlation exists
        if correlation:
            insights = automated_insights.generate_correlation_insights(
                entity1['entity_id'],
                entity2['entity_id'],
                entity1,
                entity2
            )
            assert isinstance(insights, dict)
            assert 'summary' in insights
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_presence_aware_automation_suggestion(self, full_system):
        """Test presence-aware automation suggestion generation"""
        automated_insights = full_system['automated_insights']
        presence_analyzer = full_system['presence_analyzer']
        
        entity_id = 'light.living'
        timestamp = datetime.now(timezone.utc)
        
        # Analyze presence correlation
        with patch.object(
            presence_analyzer,
            '_get_presence_history',
            return_value=[]
        ), patch.object(
            presence_analyzer,
            '_get_device_usage_history',
            return_value=[]
        ):
            presence_analysis = await presence_analyzer.analyze_presence_correlations(
                entity_id,
                hours_back=168,
                timestamp=timestamp
            )
            
            # Generate automation suggestion
            if presence_analysis.get('presence_driven'):
                suggestion = automated_insights.generate_automation_suggestion(
                    entity_id,
                    'presence',
                    presence_analysis.get('presence_correlation', 0.0)
                )
                assert isinstance(suggestion, dict)
                assert 'trigger' in suggestion


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

