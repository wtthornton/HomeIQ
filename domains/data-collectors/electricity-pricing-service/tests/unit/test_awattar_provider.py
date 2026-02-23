"""
Unit tests for AwattarProvider
Tests API response parsing, price calculations, forecast building, and edge cases
Epic 49 Story 49.6: Provider-Specific Testing
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.providers.awattar import AwattarProvider


@pytest.fixture
def awattar_provider():
    """Create AwattarProvider instance"""
    return AwattarProvider()


@pytest.fixture
def mock_awattar_response():
    """Mock Awattar API response with valid data"""
    now = datetime.now(timezone.utc)
    base_timestamp = int(now.timestamp() * 1000)
    
    # Create 24 hours of market data
    market_data = []
    for i in range(24):
        # Vary prices: cheaper at night (0-6), expensive during day (12-18)
        hour = i
        if hour < 6:
            marketprice = 2000 + (hour * 100)  # 0.20-0.25 €/kWh
        elif hour < 12:
            marketprice = 3000 + (hour * 150)  # 0.30-0.45 €/kWh
        elif hour < 18:
            marketprice = 4000 + (hour * 200)  # 0.40-0.70 €/kWh
        else:
            marketprice = 3500 - ((hour - 18) * 100)  # 0.35-0.20 €/kWh
        
        market_data.append({
            'start_timestamp': base_timestamp + (i * 3600 * 1000),
            'end_timestamp': base_timestamp + ((i + 1) * 3600 * 1000),
            'marketprice': marketprice
        })
    
    return {
        'data': market_data
    }


@pytest.fixture
def mock_empty_response():
    """Mock empty Awattar API response"""
    return {
        'data': []
    }


@pytest.fixture
def mock_invalid_response():
    """Mock invalid Awattar API response"""
    return {
        'invalid': 'data'
    }


class TestAwattarProviderParsing:
    """Test API response parsing logic"""
    
    @pytest.mark.asyncio
    async def test_parse_valid_response(self, awattar_provider, mock_awattar_response):
        """
        GIVEN: Valid Awattar API response
        WHEN: Parse response
        THEN: Should return structured pricing data
        """
        result = awattar_provider._parse_response(mock_awattar_response)
        
        assert result is not None
        assert 'current_price' in result
        assert 'currency' in result
        assert 'forecast_24h' in result
        assert 'cheapest_hours' in result
        assert 'most_expensive_hours' in result
        assert result['currency'] == 'EUR'
    
    @pytest.mark.asyncio
    async def test_parse_empty_response(self, awattar_provider, mock_empty_response):
        """
        GIVEN: Empty Awattar API response
        WHEN: Parse response
        THEN: Should return empty dict
        """
        result = awattar_provider._parse_response(mock_empty_response)
        
        assert result == {}
    
    @pytest.mark.asyncio
    async def test_parse_invalid_response(self, awattar_provider, mock_invalid_response):
        """
        GIVEN: Invalid Awattar API response (missing 'data' key)
        WHEN: Parse response
        THEN: Should return empty dict
        """
        result = awattar_provider._parse_response(mock_invalid_response)
        
        assert result == {}


class TestPriceCalculation:
    """Test price calculation logic (marketprice / 10000)"""
    
    @pytest.mark.asyncio
    async def test_price_calculation(self, awattar_provider):
        """
        GIVEN: Market price in centi-euro (marketprice)
        WHEN: Calculate price
        THEN: Should divide by 10000 to get €/kWh
        """
        # Market price: 2850 centi-euro = 0.285 €/kWh
        mock_data = {
            'data': [{
                'start_timestamp': int(datetime.now(timezone.utc).timestamp() * 1000),
                'end_timestamp': int(datetime.now(timezone.utc).timestamp() * 1000) + 3600000,
                'marketprice': 2850
            }]
        }
        
        result = awattar_provider._parse_response(mock_data)
        
        assert result['current_price'] == 0.285
    
    @pytest.mark.asyncio
    async def test_price_calculation_high_value(self, awattar_provider):
        """
        GIVEN: High market price
        WHEN: Calculate price
        THEN: Should correctly convert to €/kWh
        """
        # Market price: 5000 centi-euro = 0.50 €/kWh
        mock_data = {
            'data': [{
                'start_timestamp': int(datetime.now(timezone.utc).timestamp() * 1000),
                'end_timestamp': int(datetime.now(timezone.utc).timestamp() * 1000) + 3600000,
                'marketprice': 5000
            }]
        }
        
        result = awattar_provider._parse_response(mock_data)
        
        assert result['current_price'] == 0.50
    
    @pytest.mark.asyncio
    async def test_price_calculation_low_value(self, awattar_provider):
        """
        GIVEN: Low market price
        WHEN: Calculate price
        THEN: Should correctly convert to €/kWh
        """
        # Market price: 1000 centi-euro = 0.10 €/kWh
        mock_data = {
            'data': [{
                'start_timestamp': int(datetime.now(timezone.utc).timestamp() * 1000),
                'end_timestamp': int(datetime.now(timezone.utc).timestamp() * 1000) + 3600000,
                'marketprice': 1000
            }]
        }
        
        result = awattar_provider._parse_response(mock_data)
        
        assert result['current_price'] == 0.10


class TestForecastBuilding:
    """Test 24-hour forecast building logic"""
    
    @pytest.mark.asyncio
    async def test_forecast_24h_building(self, awattar_provider, mock_awattar_response):
        """
        GIVEN: 24 hours of market data
        WHEN: Build forecast
        THEN: Should create 24-hour forecast with correct structure
        """
        result = awattar_provider._parse_response(mock_awattar_response)
        
        assert len(result['forecast_24h']) == 24
        for i, hour_data in enumerate(result['forecast_24h']):
            assert hour_data['hour'] == i
            assert 'price' in hour_data
            assert 'timestamp' in hour_data
            assert isinstance(hour_data['timestamp'], datetime)
            assert hour_data['timestamp'].tzinfo == timezone.utc
    
    @pytest.mark.asyncio
    async def test_forecast_less_than_24_hours(self, awattar_provider):
        """
        GIVEN: Less than 24 hours of market data
        WHEN: Build forecast
        THEN: Should only include available hours
        """
        # Only 12 hours of data
        now = datetime.now(timezone.utc)
        base_timestamp = int(now.timestamp() * 1000)
        
        market_data = []
        for i in range(12):
            market_data.append({
                'start_timestamp': base_timestamp + (i * 3600 * 1000),
                'end_timestamp': base_timestamp + ((i + 1) * 3600 * 1000),
                'marketprice': 3000
            })
        
        mock_data = {'data': market_data}
        result = awattar_provider._parse_response(mock_data)
        
        assert len(result['forecast_24h']) == 12
    
    @pytest.mark.asyncio
    async def test_forecast_more_than_24_hours(self, awattar_provider):
        """
        GIVEN: More than 24 hours of market data
        WHEN: Build forecast
        THEN: Should only include first 24 hours
        """
        # 36 hours of data
        now = datetime.now(timezone.utc)
        base_timestamp = int(now.timestamp() * 1000)
        
        market_data = []
        for i in range(36):
            market_data.append({
                'start_timestamp': base_timestamp + (i * 3600 * 1000),
                'end_timestamp': base_timestamp + ((i + 1) * 3600 * 1000),
                'marketprice': 3000
            })
        
        mock_data = {'data': market_data}
        result = awattar_provider._parse_response(mock_data)
        
        assert len(result['forecast_24h']) == 24


class TestCheapestHoursCalculation:
    """Test cheapest hours calculation logic"""
    
    @pytest.mark.asyncio
    async def test_cheapest_hours_calculation(self, awattar_provider, mock_awattar_response):
        """
        GIVEN: 24 hours of market data with varying prices
        WHEN: Calculate cheapest hours
        THEN: Should return 4 cheapest hours
        """
        result = awattar_provider._parse_response(mock_awattar_response)
        
        assert 'cheapest_hours' in result
        assert len(result['cheapest_hours']) == 4
        assert all(isinstance(h, int) for h in result['cheapest_hours'])
        
        # Verify cheapest hours are actually the lowest prices
        forecast = result['forecast_24h']
        prices = [h['price'] for h in forecast]
        cheapest_prices = sorted(prices)[:4]
        
        cheapest_hour_prices = [
            forecast[h]['price'] for h in result['cheapest_hours']
        ]
        
        assert sorted(cheapest_hour_prices) == cheapest_prices
    
    @pytest.mark.asyncio
    async def test_most_expensive_hours_calculation(self, awattar_provider, mock_awattar_response):
        """
        GIVEN: 24 hours of market data with varying prices
        WHEN: Calculate most expensive hours
        THEN: Should return 4 most expensive hours
        """
        result = awattar_provider._parse_response(mock_awattar_response)
        
        assert 'most_expensive_hours' in result
        assert len(result['most_expensive_hours']) == 4
        assert all(isinstance(h, int) for h in result['most_expensive_hours'])
        
        # Verify most expensive hours are actually the highest prices
        forecast = result['forecast_24h']
        prices = [h['price'] for h in forecast]
        most_expensive_prices = sorted(prices, reverse=True)[:4]
        
        expensive_hour_prices = [
            forecast[h]['price'] for h in result['most_expensive_hours']
        ]
        
        assert sorted(expensive_hour_prices, reverse=True) == most_expensive_prices


class TestPeakPeriodDetection:
    """Test peak period detection logic"""
    
    @pytest.mark.asyncio
    async def test_peak_period_detection_high_price(self, awattar_provider):
        """
        GIVEN: Current price above median
        WHEN: Detect peak period
        THEN: Should return True
        """
        # Create data where current price (first entry) is high
        now = datetime.now(timezone.utc)
        base_timestamp = int(now.timestamp() * 1000)
        
        market_data = [
            {'start_timestamp': base_timestamp, 'end_timestamp': base_timestamp + 3600000, 'marketprice': 5000},  # High
            {'start_timestamp': base_timestamp + 3600000, 'end_timestamp': base_timestamp + 7200000, 'marketprice': 2000},  # Low
            {'start_timestamp': base_timestamp + 7200000, 'end_timestamp': base_timestamp + 10800000, 'marketprice': 3000},  # Medium
        ]
        
        mock_data = {'data': market_data}
        result = awattar_provider._parse_response(mock_data)
        
        # Current price (5000/10000 = 0.50) > median (3000/10000 = 0.30)
        assert result['peak_period'] is True
    
    @pytest.mark.asyncio
    async def test_peak_period_detection_low_price(self, awattar_provider):
        """
        GIVEN: Current price below median
        WHEN: Detect peak period
        THEN: Should return False
        """
        # Create data where current price (first entry) is low
        now = datetime.now(timezone.utc)
        base_timestamp = int(now.timestamp() * 1000)
        
        market_data = [
            {'start_timestamp': base_timestamp, 'end_timestamp': base_timestamp + 3600000, 'marketprice': 2000},  # Low
            {'start_timestamp': base_timestamp + 3600000, 'end_timestamp': base_timestamp + 7200000, 'marketprice': 5000},  # High
            {'start_timestamp': base_timestamp + 7200000, 'end_timestamp': base_timestamp + 10800000, 'marketprice': 4000},  # Medium
        ]
        
        mock_data = {'data': market_data}
        result = awattar_provider._parse_response(mock_data)
        
        # Current price (2000/10000 = 0.20) < median (4000/10000 = 0.40)
        assert result['peak_period'] is False


class TestAPIIntegration:
    """Test API integration and error handling"""
    
    @pytest.mark.asyncio
    async def test_fetch_pricing_success(self, awattar_provider, mock_awattar_response):
        """
        GIVEN: Valid API response
        WHEN: Fetch pricing
        THEN: Should return parsed data
        """
        mock_session = AsyncMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_awattar_response)
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        result = await awattar_provider.fetch_pricing(mock_session)
        
        assert result is not None
        assert 'current_price' in result
        assert 'forecast_24h' in result
    
    @pytest.mark.asyncio
    async def test_fetch_pricing_api_error(self, awattar_provider):
        """
        GIVEN: API returns error status
        WHEN: Fetch pricing
        THEN: Should raise exception
        """
        mock_session = AsyncMock()
        mock_response = MagicMock()
        mock_response.status = 500
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        with pytest.raises(Exception) as exc_info:
            await awattar_provider.fetch_pricing(mock_session)
        
        assert "status 500" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_fetch_pricing_network_error(self, awattar_provider):
        """
        GIVEN: Network error during API call
        WHEN: Fetch pricing
        THEN: Should propagate exception
        """
        mock_session = AsyncMock()
        mock_session.get.side_effect = Exception("Network error")
        
        with pytest.raises(Exception) as exc_info:
            await awattar_provider.fetch_pricing(mock_session)
        
        assert "Network error" in str(exc_info.value)


class TestEdgeCases:
    """Test edge cases and error scenarios"""
    
    @pytest.mark.asyncio
    async def test_missing_marketprice_field(self, awattar_provider):
        """
        GIVEN: Market data entry missing marketprice
        WHEN: Parse response
        THEN: Should handle gracefully (KeyError expected)
        """
        now = datetime.now(timezone.utc)
        base_timestamp = int(now.timestamp() * 1000)
        
        market_data = [{
            'start_timestamp': base_timestamp,
            'end_timestamp': base_timestamp + 3600000,
            # Missing 'marketprice'
        }]
        
        mock_data = {'data': market_data}
        
        with pytest.raises(KeyError):
            awattar_provider._parse_response(mock_data)
    
    @pytest.mark.asyncio
    async def test_invalid_timestamp_format(self, awattar_provider):
        """
        GIVEN: Invalid timestamp format in market data
        WHEN: Parse response
        THEN: Should handle gracefully
        """
        market_data = [{
            'start_timestamp': 'invalid',
            'end_timestamp': 'invalid',
            'marketprice': 3000
        }]
        
        mock_data = {'data': market_data}
        
        # Should raise TypeError when converting timestamp
        with pytest.raises((TypeError, ValueError)):
            awattar_provider._parse_response(mock_data)
    
    @pytest.mark.asyncio
    async def test_zero_marketprice(self, awattar_provider):
        """
        GIVEN: Market price is zero
        WHEN: Calculate price
        THEN: Should return 0.0
        """
        now = datetime.now(timezone.utc)
        base_timestamp = int(now.timestamp() * 1000)
        
        market_data = [{
            'start_timestamp': base_timestamp,
            'end_timestamp': base_timestamp + 3600000,
            'marketprice': 0
        }]
        
        mock_data = {'data': market_data}
        result = awattar_provider._parse_response(mock_data)
        
        assert result['current_price'] == 0.0
    
    @pytest.mark.asyncio
    async def test_negative_marketprice(self, awattar_provider):
        """
        GIVEN: Negative market price (surplus energy)
        WHEN: Calculate price
        THEN: Should return negative price
        """
        now = datetime.now(timezone.utc)
        base_timestamp = int(now.timestamp() * 1000)
        
        market_data = [{
            'start_timestamp': base_timestamp,
            'end_timestamp': base_timestamp + 3600000,
            'marketprice': -1000  # Negative price (surplus)
        }]
        
        mock_data = {'data': market_data}
        result = awattar_provider._parse_response(mock_data)
        
        assert result['current_price'] == -0.10

