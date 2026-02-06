"""
Energy Data Loader for Forecasting

Loads and preprocesses energy consumption data for forecasting models.
Supports Smart*/REFIT datasets and HomeIQ InfluxDB data.
"""

import re
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import polars as pl
import structlog

logger = structlog.get_logger(__name__)

# Regex for validating SQL identifiers to prevent injection
VALID_IDENTIFIER = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def _validate_identifier(name: str, label: str) -> str:
    """Validate SQL identifier to prevent injection."""
    if not VALID_IDENTIFIER.match(name):
        raise ValueError(f"Invalid {label}: {name!r}")
    return name


class EnergyDataLoader:
    """
    Load and preprocess energy data for forecasting.

    Supports:
    - Smart* dataset (UMass)
    - REFIT dataset (Edinburgh)
    - HomeIQ InfluxDB data
    - Generic CSV energy data
    """

    def __init__(
        self,
        data_dir: Path | None = None,
        frequency: str = "1h",  # Resample frequency
    ):
        """
        Initialize the energy data loader.

        Args:
            data_dir: Directory containing energy data files
            frequency: Resample frequency (e.g., '1h', '15m', '1d')
        """
        self.data_dir = Path(data_dir) if data_dir else Path("./data/energy")
        self.frequency = frequency

    def load_from_csv(self, path: Path) -> pl.DataFrame:
        """
        Load energy data from CSV file.

        Expected columns:
        - timestamp: DateTime
        - power or energy: Consumption value

        Args:
            path: Path to CSV file

        Returns:
            Polars DataFrame with energy data
        """
        logger.info("Loading energy data from CSV", path=str(path))

        df = pl.read_csv(path)
        df = self._standardize_columns(df)

        logger.info("Loaded rows from CSV", count=len(df), path=str(path))

        return df

    def load_from_influxdb(
        self,
        bucket: str = "home_assistant_events",
        measurement: str = "sensor",
        field: str = "power",
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        allow_synthetic_fallback: bool = False,
    ) -> pl.DataFrame:
        """
        Load energy data from HomeIQ InfluxDB.

        Args:
            bucket: InfluxDB bucket name
            measurement: Measurement name
            field: Field to query (power, energy)
            start_time: Start of time range
            end_time: End of time range
            allow_synthetic_fallback: If True, fall back to synthetic data on errors

        Returns:
            Polars DataFrame with energy data
        """
        try:
            from influxdb_client_3 import InfluxDBClient3
            import os
        except ImportError:
            if allow_synthetic_fallback:
                logger.warning("influxdb_client_3 not installed, using synthetic data")
                return self._create_synthetic_data()
            raise ImportError(
                "influxdb3-python is required for InfluxDB queries. "
                "Install with: pip install influxdb3-python"
            )

        host = os.getenv("INFLUXDB_URL", "http://localhost:8086")
        token = os.getenv("INFLUXDB_TOKEN", "")
        database = bucket  # In new API, bucket becomes database

        if not token:
            if allow_synthetic_fallback:
                logger.warning("INFLUXDB_TOKEN not set, using synthetic data")
                return self._create_synthetic_data()
            raise ValueError(
                "INFLUXDB_TOKEN environment variable is required for InfluxDB queries"
            )

        # Validate SQL identifiers to prevent injection
        field = _validate_identifier(field, "field")
        measurement = _validate_identifier(measurement, "measurement")

        # Build SQL query (new API uses SQL instead of Flux)
        if start_time is None:
            start_time = datetime.now() - timedelta(days=30)
        if end_time is None:
            end_time = datetime.now()

        # Convert to SQL query
        query = f'''
        SELECT time, {field}
        FROM {measurement}
        WHERE time >= '{start_time.isoformat()}'
          AND time <= '{end_time.isoformat()}'
        ORDER BY time
        '''

        try:
            # New API: InfluxDBClient3 with host/database parameters
            client = InfluxDBClient3(host=host, token=token, database=database)

            # Query returns pandas DataFrame
            df_pandas = client.query(query=query)

            client.close()

            if df_pandas is None or df_pandas.empty:
                if allow_synthetic_fallback:
                    logger.warning("No data returned from InfluxDB, using synthetic data")
                    return self._create_synthetic_data()
                raise ValueError("No data returned from InfluxDB query")

            # Convert pandas to polars and standardize column names
            df = pl.from_pandas(df_pandas)
            df = df.rename({"time": "timestamp", field: "power"})

            logger.info("Loaded rows from InfluxDB", count=len(df))

            return df

        except Exception as e:
            if allow_synthetic_fallback:
                logger.error("Error querying InfluxDB, using synthetic data", error=str(e))
                return self._create_synthetic_data()
            raise

    def _standardize_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        """Standardize column names."""
        columns = df.columns

        rename_map = {}
        for col in columns:
            col_lower = col.lower()

            if col_lower in ["timestamp", "time", "datetime", "date_time", "ts"]:
                rename_map[col] = "timestamp"
            elif col_lower in ["power", "watts", "active_power", "aggregate"]:
                rename_map[col] = "power"
            elif col_lower in ["energy", "kwh", "consumption"]:
                rename_map[col] = "energy"

        if rename_map:
            df = df.rename(rename_map)

        # Parse timestamp
        if "timestamp" in df.columns:
            try:
                df = df.with_columns([
                    pl.col("timestamp").str.to_datetime().alias("timestamp")
                ])
            except Exception as e:
                logger.warning(
                    "Could not parse timestamp column as datetime. "
                    "Ensure timestamps are in a standard format.",
                    error=str(e),
                )

        return df

    def _create_synthetic_data(
        self, n_days: int = 90, seed: int | None = 42
    ) -> pl.DataFrame:
        """
        Create synthetic energy data for testing.

        Generates realistic energy patterns with:
        - Daily cycles (higher during day)
        - Weekly patterns (weekends different)
        - Seasonal variations
        - Random noise

        Args:
            n_days: Number of days of data to generate
            seed: Random seed for reproducibility. None for random data.
        """
        logger.info("Creating synthetic energy data", n_days=n_days)

        # Use fixed seed only when explicitly requested (for reproducible tests)
        # In production fallback, use random seed
        if seed is not None:
            np.random.seed(seed)

        # Generate hourly timestamps
        start_time = datetime.now() - timedelta(days=n_days)
        n_samples = n_days * 24
        timestamps = [start_time + timedelta(hours=i) for i in range(n_samples)]

        # Generate energy consumption
        hour_of_day = np.array([t.hour for t in timestamps])
        day_of_week = np.array([t.weekday() for t in timestamps])
        day_of_year = np.array([t.timetuple().tm_yday for t in timestamps])

        # Base load (always-on devices)
        base_load = 200  # Watts

        # Daily pattern (higher during waking hours)
        daily_pattern = np.where(
            (hour_of_day >= 6) & (hour_of_day <= 22),
            300 + 200 * np.sin(np.pi * (hour_of_day - 6) / 16),
            100
        )

        # Peak hours (morning and evening)
        peak_pattern = np.where(
            ((hour_of_day >= 7) & (hour_of_day <= 9)) |
            ((hour_of_day >= 17) & (hour_of_day <= 21)),
            200,
            0
        )

        # Weekend adjustment (more usage during day)
        weekend_adj = np.where(day_of_week >= 5, 100, 0)

        # Seasonal pattern (more in winter/summer for heating/cooling)
        seasonal = 100 * np.cos(2 * np.pi * (day_of_year - 172) / 365)

        # Random noise
        noise = np.random.normal(0, 50, n_samples)

        # Combine
        power = base_load + daily_pattern + peak_pattern + weekend_adj + seasonal + noise
        power = np.maximum(power, 50)  # Minimum load

        df = pl.DataFrame({
            "timestamp": timestamps,
            "power": power,
        })

        return df

    def resample(self, df: pl.DataFrame, frequency: str | None = None) -> pl.DataFrame:
        """
        Resample data to specified frequency.

        Args:
            df: DataFrame with timestamp and power columns
            frequency: Resample frequency (e.g., '1h', '15m', '1d')

        Returns:
            Resampled DataFrame
        """
        freq = frequency or self.frequency

        if "timestamp" not in df.columns:
            return df

        # Sort by timestamp
        df = df.sort("timestamp")

        # Resample
        df = df.group_by_dynamic(
            "timestamp",
            every=freq,
        ).agg([
            pl.col("power").mean().alias("power"),
        ])

        return df

    def add_time_features(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Add time-based features for forecasting.

        Adds:
        - hour_of_day
        - day_of_week
        - month
        - is_weekend
        - Cyclical encodings
        """
        if "timestamp" not in df.columns:
            return df

        df = df.with_columns([
            pl.col("timestamp").dt.hour().alias("hour_of_day"),
            pl.col("timestamp").dt.weekday().alias("day_of_week"),
            pl.col("timestamp").dt.month().alias("month"),
            (pl.col("timestamp").dt.weekday() >= 5).cast(pl.Int32).alias("is_weekend"),
        ])

        # Cyclical encodings
        df = df.with_columns([
            (np.sin(2 * np.pi * pl.col("hour_of_day") / 24)).alias("hour_sin"),
            (np.cos(2 * np.pi * pl.col("hour_of_day") / 24)).alias("hour_cos"),
            (np.sin(2 * np.pi * pl.col("day_of_week") / 7)).alias("dow_sin"),
            (np.cos(2 * np.pi * pl.col("day_of_week") / 7)).alias("dow_cos"),
            (np.sin(2 * np.pi * pl.col("month") / 12)).alias("month_sin"),
            (np.cos(2 * np.pi * pl.col("month") / 12)).alias("month_cos"),
        ])

        return df

    def to_darts_timeseries(self, df: pl.DataFrame, value_col: str = "power"):
        """
        Convert to Darts TimeSeries format.

        Args:
            df: DataFrame with timestamp and value columns
            value_col: Column to use as values

        Returns:
            Darts TimeSeries object
        """
        try:
            from darts import TimeSeries
        except ImportError:
            raise ImportError("Please install darts: pip install darts>=0.30.0")

        if "timestamp" not in df.columns:
            raise ValueError(
                f"DataFrame must have a 'timestamp' column. Found: {df.columns}"
            )
        if value_col not in df.columns:
            raise ValueError(
                f"DataFrame must have a '{value_col}' column. Found: {df.columns}"
            )

        # Convert to pandas (Darts requires pandas), selecting only needed columns
        pdf = df.select(["timestamp", value_col]).to_pandas()

        # Create TimeSeries
        ts = TimeSeries.from_dataframe(
            pdf,
            time_col="timestamp",
            value_cols=value_col,
            fill_missing_dates=True,
            freq=self.frequency,
        )

        return ts

    def split_by_time(
        self,
        df: pl.DataFrame,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
    ) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
        """Split data chronologically."""
        if "timestamp" in df.columns:
            df = df.sort("timestamp")

        n = len(df)
        train_end = int(n * train_ratio)
        val_end = int(n * (train_ratio + val_ratio))

        return df[:train_end], df[train_end:val_end], df[val_end:]

    def save_processed(self, df: pl.DataFrame, output_path: Path) -> None:
        """Save processed data to Parquet."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.write_parquet(output_path)
        logger.info("Saved processed data", path=str(output_path))
