"""
Unit Tests for FeatureAnalyzer (Epic AI-2, Story AI2.3)

Tests device matching, utilization calculation, and opportunity ranking.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from src.device_intelligence.feature_analyzer import FeatureAnalyzer


class TestFeatureAnalyzer:
    """Test FeatureAnalyzer device matching and utilization analysis"""
    
    def setup_method(self):
        """Initialize mocks for each test"""
        self.mock_data_api = AsyncMock()
        self.mock_db_session = AsyncMock()  # Direct async session for testing
        self.analyzer = FeatureAnalyzer(
            data_api_client=self.mock_data_api,
            db_session=self.mock_db_session
        )
    
    # =========================================================================
    # Device Matching Tests
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_analyze_device_with_capabilities(self):
        """Test analyzing device that has capability data"""
        # Mock data-api response
        self.mock_data_api.get = AsyncMock(return_value={
            'device': {
                'device_id': 'light.kitchen_switch',
                'name': 'Kitchen Switch',
                'model': 'VZM31-SN',
                'entity_id': 'light.kitchen_switch'
            }
        })
        
        # Mock database capability lookup
        mock_capability = Mock()
        mock_capability.manufacturer = 'Inovelli'
        mock_capability.capabilities = {
            'light_control': {'type': 'composite', 'complexity': 'easy'},
            'smart_bulb_mode': {'type': 'enum', 'complexity': 'easy'},
            'led_notifications': {'type': 'composite', 'complexity': 'medium'},
            'auto_off_timer': {'type': 'numeric', 'complexity': 'medium'}
        }
        
        self.mock_db_session.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
        self.mock_db_session.return_value.__aenter__.return_value.execute = AsyncMock()
        
        # Inject capability lookup function
        async def mock_get_capability(model):
            return mock_capability if model == 'VZM31-SN' else None
        
        self.analyzer._capability_lookup = mock_get_capability
        result = await self.analyzer.analyze_device('light.kitchen_switch')
        
        # Should have analysis result
        assert result is not None
        assert result['device_id'] == 'light.kitchen_switch'
        assert result['manufacturer'] == 'Inovelli'
        assert result['model'] == 'VZM31-SN'
        assert result['total_features'] == 4
        assert result['configured_count'] == 1  # Only light_control
        assert result['utilization'] == 25.0  # 1/4 * 100
        assert len(result['unused_features']) == 3
        assert 'led_notifications' in result['unused_features']
    
    @pytest.mark.asyncio
    async def test_analyze_device_without_model(self):
        """Test device without model identifier returns None"""
        self.mock_data_api.get = AsyncMock(return_value={
            'device': {
                'device_id': 'sensor.unknown',
                'name': 'Unknown Sensor',
                'model': None  # No model
            }
        })
        
        result = await self.analyzer.analyze_device('sensor.unknown')
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_analyze_device_without_capabilities(self):
        """Test device with model but no capabilities in database"""
        self.mock_data_api.get = AsyncMock(return_value={
            'device': {
                'device_id': 'light.unknown',
                'model': 'UNKNOWN-MODEL'
            }
        })
        
        # Mock capability lookup returns None
        async def mock_get_capability(session, model):
            return None
        
        with patch('src.database.crud.get_device_capability', mock_get_capability):
            result = await self.analyzer.analyze_device('light.unknown')
        
        assert result is None
    
    # =========================================================================
    # Utilization Calculation Tests
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_utilization_calculation_partial(self):
        """Test utilization calculation with partial configuration"""
        # Mock device with 3/8 features configured = 37.5%
        self.mock_data_api.get = AsyncMock(return_value={
            'device': {
                'device_id': 'light.test',
                'model': 'TEST',
                'entity_id': 'light.test'
            }
        })
        
        mock_capability = Mock()
        mock_capability.manufacturer = 'Test'
        mock_capability.capabilities = {
            f'feature_{i}': {'type': 'test', 'complexity': 'easy'}
            for i in range(8)
        }
        # Add light_control which will be detected as configured
        mock_capability.capabilities['light_control'] = {'type': 'test', 'complexity': 'easy'}
        
        async def mock_get_capability(model):
            return mock_capability
        
        self.analyzer._capability_lookup = mock_get_capability
        result = await self.analyzer.analyze_device('light.test')
        
        # Should calculate utilization correctly
        # 1 configured (light_control) / 9 total = 11.1%
        assert result is not None
        assert result['configured_count'] == 1
        assert result['total_features'] == 9
        assert result['utilization'] == 11.1
    
    @pytest.mark.asyncio
    async def test_utilization_zero_features(self):
        """Test utilization with device that has no features"""
        self.mock_data_api.get = AsyncMock(return_value={
            'device': {'device_id': 'test', 'model': 'TEST', 'entity_id': 'light.test'}
        })
        
        mock_capability = Mock()
        mock_capability.manufacturer = 'Test'
        mock_capability.capabilities = {}  # No features
        
        async def mock_get_capability(model):
            return mock_capability
        
        self.analyzer._capability_lookup = mock_get_capability
        result = await self.analyzer.analyze_device('test')
        
        # Should handle 0 features gracefully
        assert result is not None
        assert result['utilization'] == 0.0
        assert len(result['unused_features']) == 0
    
    # =========================================================================
    # Opportunity Ranking Tests
    # =========================================================================
    
    def test_assess_impact_high(self):
        """Test high impact feature identification"""
        assert self.analyzer._assess_impact("led_notifications", {}) == "high"
        assert self.analyzer._assess_impact("power_monitoring", {}) == "high"
        assert self.analyzer._assess_impact("alert_system", {}) == "high"
    
    def test_assess_impact_medium(self):
        """Test medium impact feature identification"""
        assert self.analyzer._assess_impact("auto_off_timer", {}) == "medium"
        assert self.analyzer._assess_impact("preset_mode", {}) == "medium"
        assert self.analyzer._assess_impact("schedule_setting", {}) == "medium"
    
    def test_assess_impact_low(self):
        """Test low impact feature identification"""
        assert self.analyzer._assess_impact("unknown_feature", {}) == "low"
        assert self.analyzer._assess_impact("setting_x", {}) == "low"
    
    def test_rank_opportunities_prioritizes_high_impact_easy(self):
        """Test ranking prioritizes high impact + easy complexity"""
        opportunities = [
            {"feature_name": "low_advanced", "impact": "low", "complexity": "advanced"},  # 1 point
            {"feature_name": "high_easy", "impact": "high", "complexity": "easy"},  # 9 points
            {"feature_name": "medium_medium", "impact": "medium", "complexity": "medium"},  # 4 points
            {"feature_name": "high_medium", "impact": "high", "complexity": "medium"},  # 6 points
        ]
        
        ranked = self.analyzer._rank_opportunities(opportunities)
        
        # Should be sorted by priority score
        assert ranked[0]['feature_name'] == "high_easy"  # 9 points - top
        assert ranked[1]['feature_name'] in ["high_medium", "medium_medium"]  # 6 or 4 points
        assert ranked[-1]['feature_name'] == "low_advanced"  # 1 point - bottom
    
    # =========================================================================
    # Bulk Analysis Tests
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_analyze_all_devices_empty(self):
        """Test analyzing when no devices exist"""
        self.mock_data_api.get = AsyncMock(return_value={'devices': []})
        
        result = await self.analyzer.analyze_all_devices()
        
        assert result['overall_utilization'] == 0.0
        assert result['total_devices'] == 0
        assert result['devices_analyzed'] == 0
        assert len(result['by_manufacturer']) == 0
    
    @pytest.mark.asyncio
    async def test_analyze_all_devices_success(self):
        """Test analyzing multiple devices"""
        # Mock devices from data-api
        self.mock_data_api.get = AsyncMock(return_value={
            # Get all devices (includes model in device data)
            'devices': [
                {'device_id': 'light.switch1', 'name': 'Switch 1', 'model': 'VZM31-SN', 'entity_id': 'light.switch1'},
                {'device_id': 'light.switch2', 'name': 'Switch 2', 'model': 'VZM31-SN', 'entity_id': 'light.switch2'}
            ]
        })
        
        # Mock capabilities
        mock_capability = Mock()
        mock_capability.manufacturer = 'Inovelli'
        mock_capability.capabilities = {
            'light_control': {},
            'smart_bulb_mode': {},
            'led_notifications': {},
            'auto_off_timer': {}
        }
        
        async def mock_get_capability(model):
            return mock_capability
        
        self.analyzer._capability_lookup = mock_get_capability
        result = await self.analyzer.analyze_all_devices()
        
        # Should analyze both devices
        assert result['total_devices'] == 2
        assert result['devices_analyzed'] == 2
        assert result['overall_utilization'] == 25.0  # 1/4 for each device
        assert 'Inovelli' in result['by_manufacturer']
        assert result['by_manufacturer']['Inovelli']['devices'] == 2
    
    # =========================================================================
    # Feature Detection Tests
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_configured_features_light_entity(self):
        """Test light entity detected as having light_control configured"""
        configured = await self.analyzer._get_configured_features(
            'light.test',
            {'entity_id': 'light.test'}
        )
        
        assert 'light_control' in configured
    
    @pytest.mark.asyncio
    async def test_configured_features_switch_entity(self):
        """Test switch entity detected"""
        configured = await self.analyzer._get_configured_features(
            'switch.test',
            {'entity_id': 'switch.test'}
        )
        
        assert 'switch_control' in configured
    
    @pytest.mark.asyncio
    async def test_configured_features_climate_entity(self):
        """Test climate entity detected"""
        configured = await self.analyzer._get_configured_features(
            'climate.test',
            {'entity_id': 'climate.test'}
        )
        
        assert 'climate_control' in configured
    
    # =========================================================================
    # Performance Tests (NFR14: 100 devices in <30s)
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_analyze_100_devices_performance(self):
        """Test analyzing 100 devices completes quickly"""
        import time
        
        # Mock 100 devices
        devices = [
            {'device_id': f'light.device_{i}', 'name': f'Device {i}'}
            for i in range(100)
        ]
        
        self.mock_data_api.get = AsyncMock(return_value={
            'devices': [
                {'device_id': f'light.device_{i}', 'name': f'Device {i}', 'model': 'TEST', 'entity_id': f'light.device_{i}'}
                for i in range(100)
            ]
        })
        
        # Mock capabilities
        mock_capability = Mock()
        mock_capability.manufacturer = 'Test'
        mock_capability.capabilities = {
            'light_control': {},
            'feature_1': {},
            'feature_2': {},
            'feature_3': {}
        }
        
        async def mock_get_capability(model):
            return mock_capability
        
        self.analyzer._capability_lookup = mock_get_capability
        
        start = time.time()
        result = await self.analyzer.analyze_all_devices()
        
        duration = time.time() - start
        
        # Should complete in <30 seconds (NFR14)
        assert duration < 30
        assert result['devices_analyzed'] == 100
        assert result['analysis_duration_seconds'] < 30

