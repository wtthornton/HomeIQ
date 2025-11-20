"""
Tests for Weather Client
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from src.weather_client import OpenWeatherMapClient, WeatherData


class TestWeatherData:
    """Test cases for WeatherData class"""

    def test_weather_data_creation(self):
        """Test weather data creation from API response"""
        api_response = {
            "main": {
                "temp": 20.5,
                "feels_like": 22.0,
                "humidity": 65,
                "pressure": 1013
            },
            "weather": [{
                "main": "Clear",
                "description": "clear sky"
            }],
            "wind": {
                "speed": 3.5,
                "deg": 180
            },
            "clouds": {
                "all": 10
            },
            "visibility": 10000,
            "name": "London",
            "sys": {
                "country": "GB"
            },
            "coord": {
                "lat": 51.5074,
                "lon": -0.1278
            }
        }

        weather_data = WeatherData(api_response)

        assert weather_data.temperature == 20.5
        assert weather_data.feels_like == 22.0
        assert weather_data.humidity == 65
        assert weather_data.pressure == 1013
        assert weather_data.weather_condition == "Clear"
        assert weather_data.weather_description == "clear sky"
        assert weather_data.wind_speed == 3.5
        assert weather_data.wind_direction == 180
        assert weather_data.cloudiness == 10
        assert weather_data.visibility == 10000
        assert weather_data.location == "London"
        assert weather_data.country == "GB"
        assert weather_data.coordinates["lat"] == 51.5074
        assert weather_data.coordinates["lon"] == -0.1278
        assert weather_data.source == "openweathermap"

    def test_weather_data_to_dict(self):
        """Test weather data conversion to dictionary"""
        api_response = {
            "main": {"temp": 20.5, "humidity": 65},
            "weather": [{"main": "Clear", "description": "clear sky"}],
            "name": "London",
            "coord": {"lat": 51.5074, "lon": -0.1278}
        }

        weather_data = WeatherData(api_response)
        data_dict = weather_data.to_dict()

        assert isinstance(data_dict, dict)
        assert data_dict["temperature"] == 20.5
        assert data_dict["humidity"] == 65
        assert data_dict["weather_condition"] == "Clear"
        assert data_dict["location"] == "London"
        assert data_dict["source"] == "openweathermap"
        assert "timestamp" in data_dict


class TestOpenWeatherMapClient:
    """Test cases for OpenWeatherMapClient class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.client = OpenWeatherMapClient("test-api-key")

    def teardown_method(self):
        """Clean up after tests"""
        if self.client.session:
            asyncio.run(self.client.stop())

    def test_initialization(self):
        """Test client initialization"""
        assert self.client.api_key == "test-api-key"
        assert self.client.base_url == "https://api.openweathermap.org/data/2.5"
        assert self.client.session is None
        assert self.client.total_requests == 0
        assert self.client.successful_requests == 0
        assert self.client.failed_requests == 0
        assert self.client.rate_limit_delay == 1.0

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test starting and stopping the client"""
        # Start client
        await self.client.start()
        assert self.client.session is not None

        # Stop client
        await self.client.stop()
        assert self.client.session is None

    @pytest.mark.asyncio
    async def test_get_current_weather_success(self):
        """Test successful weather data retrieval"""
        # Mock API response
        mock_response_data = {
            "main": {"temp": 20.5, "humidity": 65},
            "weather": [{"main": "Clear", "description": "clear sky"}],
            "name": "London",
            "coord": {"lat": 51.5074, "lon": -0.1278}
        }

        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_response_data)
            mock_get.return_value.__aenter__.return_value = mock_response

            await self.client.start()
            weather_data = await self.client.get_current_weather("London")

            assert weather_data is not None
            assert weather_data.temperature == 20.5
            assert weather_data.humidity == 65
            assert weather_data.location == "London"
            assert self.client.successful_requests == 1
            assert self.client.failed_requests == 0

    @pytest.mark.asyncio
    async def test_get_current_weather_api_error(self):
        """Test API error handling"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 401
            mock_response.text = AsyncMock(return_value="Invalid API key")
            mock_get.return_value.__aenter__.return_value = mock_response

            await self.client.start()
            weather_data = await self.client.get_current_weather("London")

            assert weather_data is None
            assert self.client.successful_requests == 0
            assert self.client.failed_requests == 1
            assert "Invalid API key" in self.client.last_error

    @pytest.mark.asyncio
    async def test_get_current_weather_timeout(self):
        """Test timeout handling"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = asyncio.TimeoutError()

            await self.client.start()
            weather_data = await self.client.get_current_weather("London")

            assert weather_data is None
            assert self.client.failed_requests == 1
            assert self.client.last_error == "Request timeout"

    @pytest.mark.asyncio
    async def test_get_current_weather_by_coordinates(self):
        """Test weather retrieval by coordinates"""
        mock_response_data = {
            "main": {"temp": 20.5},
            "weather": [{"main": "Clear"}],
            "name": "London",
            "coord": {"lat": 51.5074, "lon": -0.1278}
        }

        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_response_data)
            mock_get.return_value.__aenter__.return_value = mock_response

            await self.client.start()
            weather_data = await self.client.get_current_weather_by_coordinates(51.5074, -0.1278)

            assert weather_data is not None
            assert weather_data.temperature == 20.5

    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting functionality"""
        mock_response_data = {
            "main": {"temp": 20.5},
            "weather": [{"main": "Clear"}],
            "name": "London"
        }

        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_response_data)
            mock_get.return_value.__aenter__.return_value = mock_response

            await self.client.start()

            # Configure short rate limit for testing
            self.client.configure_rate_limit(0.1)

            # Make two requests quickly
            start_time = asyncio.get_event_loop().time()
            await self.client.get_current_weather("London")
            await self.client.get_current_weather("Paris")
            end_time = asyncio.get_event_loop().time()

            # Should have taken at least 0.1 seconds due to rate limiting
            assert end_time - start_time >= 0.1

    def test_configure_rate_limit(self):
        """Test rate limit configuration"""
        self.client.configure_rate_limit(2.0)
        assert self.client.rate_limit_delay == 2.0

        # Test invalid rate limit
        with pytest.raises(ValueError):
            self.client.configure_rate_limit(-1.0)

    def test_get_statistics(self):
        """Test getting client statistics"""
        # Set some statistics
        self.client.total_requests = 10
        self.client.successful_requests = 8
        self.client.failed_requests = 2
        self.client.last_error = "Test error"

        stats = self.client.get_statistics()

        assert stats["total_requests"] == 10
        assert stats["successful_requests"] == 8
        assert stats["failed_requests"] == 2
        assert stats["success_rate"] == 80.0
        assert stats["last_error"] == "Test error"
        assert stats["rate_limit_delay"] == 1.0

    def test_reset_statistics(self):
        """Test resetting statistics"""
        # Set some statistics
        self.client.total_requests = 10
        self.client.successful_requests = 8
        self.client.failed_requests = 2
        self.client.last_error = "Test error"

        # Reset statistics
        self.client.reset_statistics()

        assert self.client.total_requests == 0
        assert self.client.successful_requests == 0
        assert self.client.failed_requests == 0
        assert self.client.last_error is None
