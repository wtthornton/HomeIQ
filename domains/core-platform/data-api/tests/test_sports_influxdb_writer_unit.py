"""Unit tests for SportsInfluxDBWriter — Story 85.6

Tests point construction, write dispatch, stats tracking, and error handling
with mocked InfluxDB client.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.sports_influxdb_writer import SportsInfluxDBWriter, get_sports_writer


class TestConnect:

    @pytest.mark.asyncio
    async def test_connect_no_token_returns_false(self):
        writer = SportsInfluxDBWriter()
        writer.token = None
        assert await writer.connect() is False
        assert writer.is_connected is False

    @pytest.mark.asyncio
    async def test_connect_no_influxdb_package_returns_false(self):
        writer = SportsInfluxDBWriter()
        writer.token = "test-token"
        with patch("src.sports_influxdb_writer.InfluxDBClient", None):
            assert await writer.connect() is False

    @pytest.mark.asyncio
    async def test_connect_success(self):
        writer = SportsInfluxDBWriter()
        writer.token = "test-token"

        mock_client = MagicMock()
        mock_write_api = MagicMock()
        mock_client.write_api.return_value = mock_write_api

        with patch("src.sports_influxdb_writer.InfluxDBClient", return_value=mock_client), \
             patch("src.sports_influxdb_writer.SYNCHRONOUS", "sync"):
            result = await writer.connect()
            assert result is True
            assert writer.is_connected is True

    @pytest.mark.asyncio
    async def test_connect_exception_returns_false(self):
        writer = SportsInfluxDBWriter()
        writer.token = "test-token"
        with patch("src.sports_influxdb_writer.InfluxDBClient", side_effect=Exception("fail")):
            assert await writer.connect() is False
            assert writer.is_connected is False


class TestWriteNFLGame:

    def _make_writer(self):
        writer = SportsInfluxDBWriter()
        writer.is_connected = True
        writer.write_api = MagicMock()
        return writer

    @pytest.mark.asyncio
    async def test_not_connected_returns_false(self):
        writer = SportsInfluxDBWriter()
        assert await writer.write_nfl_game({}) is False

    @pytest.mark.asyncio
    async def test_writes_game_data(self):
        writer = self._make_writer()
        game = {
            "game_id": "NFL-2025-W1-1",
            "season": "2025",
            "week": "1",
            "home_team": "KC",
            "away_team": "BAL",
            "status": "final",
            "home_score": 27,
            "away_score": 20,
            "quarter": "4",
            "time_remaining": "0:00",
            "start_time": "2025-09-05T20:20:00Z",
        }
        with patch("src.sports_influxdb_writer.asyncio") as mock_asyncio:
            mock_asyncio.to_thread = AsyncMock()
            result = await writer.write_nfl_game(game)
            assert result is True
            assert writer.total_points_written == 1

    @pytest.mark.asyncio
    async def test_write_exception_increments_failed(self):
        writer = self._make_writer()
        with patch("src.sports_influxdb_writer.asyncio") as mock_asyncio:
            mock_asyncio.to_thread = AsyncMock(side_effect=Exception("write error"))
            result = await writer.write_nfl_game({"game_id": "1"})
            assert result is False
            assert writer.total_points_failed == 1

    @pytest.mark.asyncio
    async def test_handles_alternative_field_names(self):
        """Tests homeTeam/awayTeam/homeScore/awayScore alternatives."""
        writer = self._make_writer()
        game = {
            "game_id": "1",
            "homeTeam": "KC",
            "awayTeam": "BAL",
            "homeScore": 27,
            "awayScore": 20,
            "startTime": "2025-09-05T20:20:00Z",
        }
        with patch("src.sports_influxdb_writer.asyncio") as mock_asyncio:
            mock_asyncio.to_thread = AsyncMock()
            result = await writer.write_nfl_game(game)
            assert result is True


class TestWriteNHLGame:

    @pytest.mark.asyncio
    async def test_not_connected_returns_false(self):
        writer = SportsInfluxDBWriter()
        assert await writer.write_nhl_game({}) is False

    @pytest.mark.asyncio
    async def test_writes_nhl_game(self):
        writer = SportsInfluxDBWriter()
        writer.is_connected = True
        writer.write_api = MagicMock()
        game = {
            "game_id": "NHL-2025-1",
            "home_team": "BOS",
            "away_team": "NYR",
            "home_score": 3,
            "away_score": 2,
            "period": "3",
        }
        with patch("src.sports_influxdb_writer.asyncio") as mock_asyncio:
            mock_asyncio.to_thread = AsyncMock()
            result = await writer.write_nhl_game(game)
            assert result is True


    @pytest.mark.asyncio
    async def test_writes_nhl_game_all_fields(self):
        writer = SportsInfluxDBWriter()
        writer.is_connected = True
        writer.write_api = MagicMock()
        game = {
            "game_id": "NHL-2025-2",
            "season": 2025,
            "home_team": "CBJ",
            "away_team": "PIT",
            "home_score": 4,
            "away_score": 1,
            "status": "finished",
            "period": "3",
            "time_remaining": "00:00",
            "start_time": "2025-10-01T19:00:00Z",
        }
        with patch("src.sports_influxdb_writer.asyncio") as mock_asyncio:
            mock_asyncio.to_thread = AsyncMock()
            result = await writer.write_nhl_game(game)
            assert result is True
            assert writer.total_points_written >= 1

    @pytest.mark.asyncio
    async def test_writes_nhl_game_exception(self):
        writer = SportsInfluxDBWriter()
        writer.is_connected = True
        writer.write_api = MagicMock()
        with patch("src.sports_influxdb_writer.asyncio") as mock_asyncio:
            mock_asyncio.to_thread = AsyncMock(side_effect=Exception("write error"))
            result = await writer.write_nhl_game({"game_id": "1"})
            assert result is False
            assert writer.total_points_failed >= 1

    @pytest.mark.asyncio
    async def test_writes_nfl_game_datetime_start_time(self):
        """Test with datetime (not string) start_time."""
        writer = SportsInfluxDBWriter()
        writer.is_connected = True
        writer.write_api = MagicMock()
        from datetime import datetime
        game = {
            "game_id": "NFL-2025-3",
            "home_team": "CLE",
            "away_team": "BAL",
            "home_score": 20,
            "away_score": 17,
            "start_time": datetime(2025, 9, 5, 20, 20),
        }
        with patch("src.sports_influxdb_writer.asyncio") as mock_asyncio:
            mock_asyncio.to_thread = AsyncMock()
            result = await writer.write_nfl_game(game)
            assert result is True


class TestWriteGame:

    def setup_method(self):
        self.writer = SportsInfluxDBWriter()
        self.writer.is_connected = True
        self.writer.write_api = MagicMock()

    @pytest.mark.asyncio
    async def test_dispatches_nfl(self):
        with patch.object(self.writer, "write_nfl_game", new_callable=AsyncMock, return_value=True):
            result = await self.writer.write_game({"league": "NFL"})
            assert result is True

    @pytest.mark.asyncio
    async def test_dispatches_nhl(self):
        with patch.object(self.writer, "write_nhl_game", new_callable=AsyncMock, return_value=True):
            result = await self.writer.write_game({"league": "NHL"})
            assert result is True

    @pytest.mark.asyncio
    async def test_unknown_league_returns_false(self):
        result = await self.writer.write_game({"league": "MLB"})
        assert result is False

    @pytest.mark.asyncio
    async def test_empty_league_returns_false(self):
        result = await self.writer.write_game({})
        assert result is False


class TestGetStats:

    def test_returns_stats_dict(self):
        writer = SportsInfluxDBWriter()
        writer.total_points_written = 10
        writer.total_points_failed = 2
        stats = writer.get_stats()
        assert stats["connected"] is False
        assert stats["total_points_written"] == 10
        assert stats["total_points_failed"] == 2
        assert stats["bucket"] == "sports_data"


class TestClose:

    @pytest.mark.asyncio
    async def test_close_sets_not_connected(self):
        writer = SportsInfluxDBWriter()
        writer.is_connected = True
        writer.client = MagicMock()
        writer.write_api = MagicMock()
        await writer.close()
        assert writer.is_connected is False


class TestSingleton:

    def test_returns_same_instance(self):
        import src.sports_influxdb_writer as mod
        mod._sports_writer = None
        assert get_sports_writer() is get_sports_writer()
