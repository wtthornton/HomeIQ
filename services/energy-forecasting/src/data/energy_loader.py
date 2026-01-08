"""
Energy Data Loader for Forecasting

Loads and preprocesses energy consumption data for forecasting models.
Supports Smart*/REFIT datasets and HomeIQ InfluxDB data.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

logger = logging.getLogger(__name__)


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
        logger.info(f"Loading energy data from {path}")
        
        df = pl.read_csv(path)
        df = self._standardize_columns(df)
        
        logger.info(f"Loaded {len(df):,} rows from {path}")
        
        return df
    
    def load_from_influxdb(
        self,
        bucket: str = "home_assistant_events",
        measurement: str = "sensor",
        field: str = "power",
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> pl.DataFrame:
        """
        Load energy data from HomeIQ InfluxDB.
        
        Args:
            bucket: InfluxDB bucket name
            measurement: Measurement name
            field: Field to query (power, energy)
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            Polars DataFrame with energy data
        """
        try:
            from influxdb_client import InfluxDBClient
            import os
        except ImportError:
            logger.warning("influxdb_client not installed")
            return self._create_synthetic_data()
        
        url = os.getenv("INFLUXDB_URL", "http://localhost:8086")
        token = os.getenv("INFLUXDB_TOKEN", "")
        org = os.getenv("INFLUXDB_ORG", "homeiq")
        
        if not token:
            logger.warning("INFLUXDB_TOKEN not set, using synthetic data")
            return self._create_synthetic_data()
        
        # Build Flux query
        if start_time is None:
            start_time = datetime.now() - timedelta(days=30)
        if end_time is None:
            end_time = datetime.now()
        
        query = f'''
        from(bucket: "{bucket}")
            |> range(start: {start_time.isoformat()}Z, stop: {end_time.isoformat()}Z)
            |> filter(fn: (r) => r._measurement == "{measurement}")
            |> filter(fn: (r) => r._field == "{field}")
            |> aggregateWindow(every: {self.frequency}, fn: mean, createEmpty: false)
        '''
        
        try:
            client = InfluxDBClient(url=url, token=token, org=org)
            query_api = client.query_api()
            
            tables = query_api.query(query)
            
            records = []
            for table in tables:
                for record in table.records:
                    records.append({
                        "timestamp": record.get_time(),
                        "power": record.get_value(),
                    })
            
            client.close()
            
            if not records:
                logger.warning("No data returned from InfluxDB")
                return self._create_synthetic_data()
            
            df = pl.DataFrame(records)
            logger.info(f"Loaded {len(df):,} rows from InfluxDB")
            
            return df
            
        except Exception as e:
            logger.error(f"Error querying InfluxDB: {e}")
            return self._create_synthetic_data()
    
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
            except Exception:
                pass
        
        return df
    
    def _create_synthetic_data(self, n_days: int = 90) -> pl.DataFrame:
        """
        Create synthetic energy data for testing.
        
        Generates realistic energy patterns with:
        - Daily cycles (higher during day)
        - Weekly patterns (weekends different)
        - Seasonal variations
        - Random noise
        """
        logger.info(f"Creating synthetic energy data ({n_days} days)")
        
        np.random.seed(42)
        
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
        
        # Convert to pandas (Darts requires pandas)
        pdf = df.to_pandas()
        
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
        logger.info(f"Saved to {output_path}")


def main():
    """Example usage."""
    logging.basicConfig(level=logging.INFO)
    
    loader = EnergyDataLoader()
    
    # Create synthetic data
    df = loader._create_synthetic_data(n_days=30)
    print(f"Loaded {len(df):,} samples")
    print(f"Columns: {df.columns}")
    print(f"\nSample:\n{df.head()}")
    
    # Add features
    df = loader.add_time_features(df)
    print(f"\nWith features:\n{df.head()}")
    
    # Convert to Darts
    try:
        ts = loader.to_darts_timeseries(df)
        print(f"\nDarts TimeSeries: {ts}")
    except ImportError:
        print("\nDarts not installed, skipping TimeSeries conversion")


if __name__ == "__main__":
    main()
