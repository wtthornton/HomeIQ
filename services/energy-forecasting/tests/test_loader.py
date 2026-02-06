"""Unit tests for EnergyDataLoader."""

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import polars as pl
import pytest


class TestEnergyDataLoaderInit:
    """Tests for EnergyDataLoader initialization."""

    def test_default_init(self):
        """Test default initialization."""
        from src.data.energy_loader import EnergyDataLoader

        loader = EnergyDataLoader()
        assert loader.data_dir == Path("./data/energy")
        assert loader.frequency == "1h"

    def test_custom_init(self, temp_dir):
        """Test custom initialization."""
        from src.data.energy_loader import EnergyDataLoader

        loader = EnergyDataLoader(data_dir=temp_dir, frequency="15m")
        assert loader.data_dir == temp_dir
        assert loader.frequency == "15m"


class TestSyntheticData:
    """Tests for synthetic data generation."""

    def test_creates_correct_shape(self):
        """Test that synthetic data has correct number of rows."""
        from src.data.energy_loader import EnergyDataLoader

        loader = EnergyDataLoader()
        df = loader._create_synthetic_data(n_days=7)

        expected_rows = 7 * 24
        assert len(df) == expected_rows

    def test_has_required_columns(self):
        """Test that synthetic data has timestamp and power columns."""
        from src.data.energy_loader import EnergyDataLoader

        loader = EnergyDataLoader()
        df = loader._create_synthetic_data(n_days=7)

        assert "timestamp" in df.columns
        assert "power" in df.columns

    def test_power_values_positive(self):
        """Test that all power values are positive."""
        from src.data.energy_loader import EnergyDataLoader

        loader = EnergyDataLoader()
        df = loader._create_synthetic_data(n_days=7)

        assert (df["power"] >= 50).all()

    def test_fixed_seed_reproducible(self):
        """Test that fixed seed produces same data."""
        from src.data.energy_loader import EnergyDataLoader

        loader = EnergyDataLoader()
        df1 = loader._create_synthetic_data(n_days=7, seed=42)
        df2 = loader._create_synthetic_data(n_days=7, seed=42)

        np.testing.assert_array_equal(
            df1["power"].to_numpy(),
            df2["power"].to_numpy(),
        )

    def test_no_seed_varies(self):
        """Test that None seed produces different data."""
        from src.data.energy_loader import EnergyDataLoader

        loader = EnergyDataLoader()
        df1 = loader._create_synthetic_data(n_days=7, seed=None)
        df2 = loader._create_synthetic_data(n_days=7, seed=None)

        # With no seed, data should differ (extremely unlikely to be identical)
        # We can't guarantee this with 100% certainty, but practically it will differ
        assert not np.array_equal(
            df1["power"].to_numpy(),
            df2["power"].to_numpy(),
        )


class TestStandardizeColumns:
    """Tests for column standardization."""

    def test_renames_time_to_timestamp(self):
        """Test renaming 'time' column to 'timestamp'."""
        from src.data.energy_loader import EnergyDataLoader

        loader = EnergyDataLoader()
        df = pl.DataFrame({
            "time": ["2024-01-01 00:00:00", "2024-01-01 01:00:00"],
            "watts": [100.0, 200.0],
        })

        result = loader._standardize_columns(df)
        assert "timestamp" in result.columns
        assert "power" in result.columns

    def test_renames_datetime_to_timestamp(self):
        """Test renaming 'DateTime' column to 'timestamp'."""
        from src.data.energy_loader import EnergyDataLoader

        loader = EnergyDataLoader()
        df = pl.DataFrame({
            "DateTime": ["2024-01-01 00:00:00"],
            "Active_Power": [150.0],
        })

        result = loader._standardize_columns(df)
        assert "timestamp" in result.columns
        assert "power" in result.columns

    def test_renames_energy_columns(self):
        """Test renaming energy-related columns."""
        from src.data.energy_loader import EnergyDataLoader

        loader = EnergyDataLoader()
        df = pl.DataFrame({
            "ts": ["2024-01-01 00:00:00"],
            "kwh": [1.5],
        })

        result = loader._standardize_columns(df)
        assert "timestamp" in result.columns
        assert "energy" in result.columns

    def test_no_matching_columns_unchanged(self):
        """Test that unrecognized columns are left unchanged."""
        from src.data.energy_loader import EnergyDataLoader

        loader = EnergyDataLoader()
        df = pl.DataFrame({
            "foo": [1],
            "bar": [2],
        })

        result = loader._standardize_columns(df)
        assert "foo" in result.columns
        assert "bar" in result.columns


class TestSQLIdentifierValidation:
    """Tests for SQL identifier validation."""

    def test_valid_identifiers(self):
        """Test that valid identifiers pass validation."""
        from src.data.energy_loader import _validate_identifier

        assert _validate_identifier("power", "field") == "power"
        assert _validate_identifier("sensor_data", "measurement") == "sensor_data"
        assert _validate_identifier("_private", "field") == "_private"
        assert _validate_identifier("A1", "field") == "A1"

    def test_invalid_identifiers_raise(self):
        """Test that invalid identifiers raise ValueError."""
        from src.data.energy_loader import _validate_identifier

        with pytest.raises(ValueError, match="Invalid field"):
            _validate_identifier("'; DROP TABLE --", "field")

        with pytest.raises(ValueError, match="Invalid measurement"):
            _validate_identifier("table name", "measurement")

        with pytest.raises(ValueError, match="Invalid field"):
            _validate_identifier("123abc", "field")

        with pytest.raises(ValueError, match="Invalid field"):
            _validate_identifier("", "field")


class TestInfluxDBLoading:
    """Tests for InfluxDB data loading."""

    def test_missing_import_without_fallback_raises(self):
        """Test that missing influxdb_client_3 raises ImportError when fallback disabled."""
        from src.data.energy_loader import EnergyDataLoader

        loader = EnergyDataLoader()

        with patch.dict("sys.modules", {"influxdb_client_3": None}):
            with pytest.raises(ImportError, match="influxdb3-python is required"):
                loader.load_from_influxdb(allow_synthetic_fallback=False)

    def test_missing_import_with_fallback_returns_synthetic(self):
        """Test that missing module with fallback returns synthetic data."""
        from src.data.energy_loader import EnergyDataLoader

        loader = EnergyDataLoader()

        with patch.dict("sys.modules", {"influxdb_client_3": None}):
            df = loader.load_from_influxdb(allow_synthetic_fallback=True)
            assert len(df) > 0
            assert "timestamp" in df.columns
            assert "power" in df.columns

    def test_missing_token_without_fallback_raises(self):
        """Test that missing token raises ValueError when fallback disabled."""
        from src.data.energy_loader import EnergyDataLoader

        loader = EnergyDataLoader()

        mock_module = MagicMock()
        with patch.dict("sys.modules", {"influxdb_client_3": mock_module}):
            with patch.dict("os.environ", {"INFLUXDB_TOKEN": ""}, clear=False):
                with pytest.raises(ValueError, match="INFLUXDB_TOKEN"):
                    loader.load_from_influxdb(allow_synthetic_fallback=False)

    def test_sql_injection_field_rejected(self):
        """Test that SQL injection attempts in field parameter are rejected."""
        from src.data.energy_loader import EnergyDataLoader

        loader = EnergyDataLoader()

        mock_module = MagicMock()
        with patch.dict("sys.modules", {"influxdb_client_3": mock_module}):
            with patch.dict("os.environ", {"INFLUXDB_TOKEN": "test_token"}, clear=False):
                with pytest.raises(ValueError, match="Invalid field"):
                    loader.load_from_influxdb(
                        field="power; DROP TABLE sensor",
                        allow_synthetic_fallback=False,
                    )


class TestToDartsTimeseries:
    """Tests for Darts TimeSeries conversion."""

    def test_missing_timestamp_column_raises(self):
        """Test that missing timestamp column raises ValueError."""
        from src.data.energy_loader import EnergyDataLoader

        loader = EnergyDataLoader()
        df = pl.DataFrame({"power": [1.0, 2.0, 3.0]})

        with pytest.raises(ValueError, match="'timestamp' column"):
            loader.to_darts_timeseries(df)

    def test_missing_value_column_raises(self):
        """Test that missing value column raises ValueError."""
        from src.data.energy_loader import EnergyDataLoader

        loader = EnergyDataLoader()
        df = pl.DataFrame({
            "timestamp": [datetime(2024, 1, 1), datetime(2024, 1, 2)],
        })

        with pytest.raises(ValueError, match="'power' column"):
            loader.to_darts_timeseries(df)

    def test_valid_conversion(self, sample_polars_df):
        """Test successful conversion to Darts TimeSeries."""
        from src.data.energy_loader import EnergyDataLoader

        loader = EnergyDataLoader()
        ts = loader.to_darts_timeseries(sample_polars_df)

        assert ts is not None
        assert len(ts) > 0


class TestResample:
    """Tests for data resampling."""

    def test_resample_uses_default_frequency(self, sample_polars_df):
        """Test that resample uses the loader's default frequency."""
        from src.data.energy_loader import EnergyDataLoader

        loader = EnergyDataLoader(frequency="1h")
        result = loader.resample(sample_polars_df)

        assert "timestamp" in result.columns
        assert "power" in result.columns

    def test_resample_no_timestamp_returns_unchanged(self):
        """Test that resample returns unchanged df without timestamp column."""
        from src.data.energy_loader import EnergyDataLoader

        loader = EnergyDataLoader()
        df = pl.DataFrame({"value": [1, 2, 3]})
        result = loader.resample(df)

        assert result.frame_equal(df)


class TestTimeFeatures:
    """Tests for time feature engineering."""

    def test_adds_time_features(self, sample_polars_df):
        """Test that time features are added."""
        from src.data.energy_loader import EnergyDataLoader

        loader = EnergyDataLoader()
        result = loader.add_time_features(sample_polars_df)

        assert "hour_of_day" in result.columns
        assert "day_of_week" in result.columns
        assert "month" in result.columns
        assert "is_weekend" in result.columns
        assert "hour_sin" in result.columns
        assert "hour_cos" in result.columns

    def test_no_timestamp_returns_unchanged(self):
        """Test that df without timestamp is returned unchanged."""
        from src.data.energy_loader import EnergyDataLoader

        loader = EnergyDataLoader()
        df = pl.DataFrame({"value": [1, 2, 3]})
        result = loader.add_time_features(df)

        assert result.columns == ["value"]


class TestSplitByTime:
    """Tests for chronological data splitting."""

    def test_split_ratios(self, sample_polars_df):
        """Test that split produces correct proportions."""
        from src.data.energy_loader import EnergyDataLoader

        loader = EnergyDataLoader()
        train, val, test = loader.split_by_time(
            sample_polars_df, train_ratio=0.7, val_ratio=0.15
        )

        total = len(sample_polars_df)
        assert len(train) == int(total * 0.7)
        assert len(val) == int(total * 0.85) - int(total * 0.7)
        # test gets the remainder

    def test_split_covers_all_data(self, sample_polars_df):
        """Test that all splits together contain all data."""
        from src.data.energy_loader import EnergyDataLoader

        loader = EnergyDataLoader()
        train, val, test = loader.split_by_time(sample_polars_df)

        assert len(train) + len(val) + len(test) == len(sample_polars_df)


class TestSaveProcessed:
    """Tests for saving processed data."""

    def test_save_parquet(self, sample_polars_df, temp_dir):
        """Test saving data to Parquet format."""
        from src.data.energy_loader import EnergyDataLoader

        loader = EnergyDataLoader()
        output_path = temp_dir / "output.parquet"

        loader.save_processed(sample_polars_df, output_path)
        assert output_path.exists()

        # Verify we can read it back
        loaded = pl.read_parquet(output_path)
        assert len(loaded) == len(sample_polars_df)
