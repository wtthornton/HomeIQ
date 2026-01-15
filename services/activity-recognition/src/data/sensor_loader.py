"""
Sensor Data Loader for Activity Recognition

Loads and preprocesses sensor datasets for activity recognition:
- Smart* Data Set (UMass) - Multi-home sensor streams
- REFIT Smart Home Dataset - 20 UK homes with activity labels

These datasets provide real-world sensor data for training
activity recognition models.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path

import polars as pl
import numpy as np

logger = logging.getLogger(__name__)


# Activity labels for classification
ACTIVITY_LABELS = {
    0: "sleeping",
    1: "waking",
    2: "leaving",
    3: "arriving",
    4: "cooking",
    5: "eating",
    6: "working",
    7: "watching_tv",
    8: "relaxing",
    9: "other",
}

# Sensor types commonly found in smart home datasets
SENSOR_TYPES = {
    "motion": "binary",
    "door": "binary",
    "window": "binary",
    "temperature": "continuous",
    "humidity": "continuous",
    "light": "continuous",
    "power": "continuous",
    "energy": "continuous",
}


class SensorDataLoader:
    """
    Load and preprocess sensor datasets for activity recognition.
    
    Supports:
    - Smart* Data Set (UMass Trace Repository)
    - REFIT Smart Home Dataset (Edinburgh Research)
    - Generic CSV sensor data
    
    Features:
    - Polars-based processing for performance
    - Sequence creation for LSTM training
    - Activity label mapping
    - Feature engineering for sensor data
    """
    
    def __init__(
        self,
        data_dir: Path | None = None,
        sequence_length: int = 30,  # 30 time steps
        step_size: int = 1,  # Sliding window step
    ):
        """
        Initialize the sensor data loader.
        
        Args:
            data_dir: Directory containing sensor data files
            sequence_length: Number of time steps per sequence
            step_size: Step size for sliding window
        """
        self.data_dir = Path(data_dir) if data_dir else Path("./data/sensors")
        self.sequence_length = sequence_length
        self.step_size = step_size
    
    def load_smart_star(self, path: Path | None = None) -> pl.DataFrame:
        """
        Load Smart* dataset from UMass.
        
        The Smart* dataset contains:
        - Energy consumption data
        - Motion sensor data
        - Environmental sensors
        - Activity labels
        
        Args:
            path: Path to Smart* data directory
            
        Returns:
            Polars DataFrame with sensor data
        """
        data_path = path or self.data_dir / "smart_star"
        
        if not data_path.exists():
            logger.warning(f"Smart* data directory not found: {data_path}")
            return self._create_synthetic_data()
        
        logger.info(f"Loading Smart* dataset from {data_path}")
        
        # Smart* data is typically in CSV format
        # Structure varies by home, so we handle multiple formats
        all_data = []
        
        for csv_file in data_path.glob("*.csv"):
            try:
                df = pl.read_csv(csv_file)
                df = df.with_columns([
                    pl.lit(csv_file.stem).alias("source_file")
                ])
                all_data.append(df)
            except Exception as e:
                logger.warning(f"Failed to load {csv_file}: {e}")
        
        if not all_data:
            logger.warning("No CSV files found, using synthetic data")
            return self._create_synthetic_data()
        
        # Combine all data
        combined = pl.concat(all_data, how="diagonal")
        
        # Standardize column names
        combined = self._standardize_columns(combined)
        
        logger.info(f"Loaded {len(combined):,} rows from Smart* dataset")
        
        return combined
    
    def load_refit(self, path: Path | None = None) -> pl.DataFrame:
        """
        Load REFIT Smart Home dataset.
        
        The REFIT dataset contains:
        - Aggregate and appliance-level power consumption
        - Activity labels from 20 UK homes
        - Pre and post smart home installation data
        
        Args:
            path: Path to REFIT data directory
            
        Returns:
            Polars DataFrame with sensor data
        """
        data_path = path or self.data_dir / "refit"
        
        if not data_path.exists():
            logger.warning(f"REFIT data directory not found: {data_path}")
            return self._create_synthetic_data()
        
        logger.info(f"Loading REFIT dataset from {data_path}")
        
        all_data = []
        
        # REFIT has data per house (House_1, House_2, etc.)
        for house_dir in sorted(data_path.glob("House_*")):
            if house_dir.is_dir():
                for csv_file in house_dir.glob("*.csv"):
                    try:
                        df = pl.read_csv(csv_file)
                        df = df.with_columns([
                            pl.lit(house_dir.name).alias("house_id"),
                            pl.lit(csv_file.stem).alias("appliance"),
                        ])
                        all_data.append(df)
                    except Exception as e:
                        logger.warning(f"Failed to load {csv_file}: {e}")
        
        if not all_data:
            logger.warning("No REFIT data found, using synthetic data")
            return self._create_synthetic_data()
        
        combined = pl.concat(all_data, how="diagonal")
        combined = self._standardize_columns(combined)
        
        logger.info(f"Loaded {len(combined):,} rows from REFIT dataset")
        
        return combined
    
    def load_generic_csv(self, path: Path) -> pl.DataFrame:
        """
        Load generic CSV sensor data.
        
        Expected columns:
        - timestamp: DateTime column
        - motion, door, temperature, etc.: Sensor values
        - activity_label (optional): Activity classification
        
        Args:
            path: Path to CSV file
            
        Returns:
            Polars DataFrame with sensor data
        """
        logger.info(f"Loading sensor data from {path}")
        
        df = pl.read_csv(path)
        df = self._standardize_columns(df)
        
        logger.info(f"Loaded {len(df):,} rows from {path}")
        
        return df
    
    def _standardize_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Standardize column names and types.
        
        Maps various column naming conventions to standard names.
        """
        columns = df.columns
        
        # Column name mappings
        timestamp_cols = ["timestamp", "time", "datetime", "date_time", "ts"]
        motion_cols = ["motion", "pir", "motion_sensor", "movement"]
        door_cols = ["door", "door_sensor", "contact", "entry"]
        temp_cols = ["temperature", "temp", "ambient_temp"]
        humidity_cols = ["humidity", "rh", "relative_humidity"]
        power_cols = ["power", "watts", "active_power", "aggregate"]
        energy_cols = ["energy", "kwh", "consumption"]
        activity_cols = ["activity", "activity_label", "label", "state"]
        
        rename_map = {}
        
        for col in columns:
            col_lower = col.lower()
            
            if col_lower in timestamp_cols:
                rename_map[col] = "timestamp"
            elif col_lower in motion_cols:
                rename_map[col] = "motion"
            elif col_lower in door_cols:
                rename_map[col] = "door"
            elif col_lower in temp_cols:
                rename_map[col] = "temperature"
            elif col_lower in humidity_cols:
                rename_map[col] = "humidity"
            elif col_lower in power_cols:
                rename_map[col] = "power"
            elif col_lower in energy_cols:
                rename_map[col] = "energy"
            elif col_lower in activity_cols:
                rename_map[col] = "activity_label"
        
        if rename_map:
            df = df.rename(rename_map)
        
        # Parse timestamp if present
        if "timestamp" in df.columns:
            try:
                df = df.with_columns([
                    pl.col("timestamp").str.to_datetime().alias("timestamp")
                ])
            except Exception:
                pass  # Already datetime or unparseable
        
        return df
    
    def _create_synthetic_data(self, n_samples: int = 10000) -> pl.DataFrame:
        """
        Create synthetic sensor data for testing.
        
        Generates realistic sensor patterns with activity labels.
        """
        logger.info(f"Creating synthetic sensor data ({n_samples:,} samples)")
        
        np.random.seed(42)
        
        # Generate timestamps (1 minute intervals)
        start_time = datetime(2024, 1, 1)
        timestamps = [start_time + timedelta(minutes=i) for i in range(n_samples)]
        
        # Generate sensor values with realistic patterns
        hour_of_day = np.array([t.hour for t in timestamps])
        
        # Motion: Higher during day, lower at night
        motion_prob = np.where(
            (hour_of_day >= 7) & (hour_of_day <= 22),
            0.3,  # Day
            0.05  # Night
        )
        motion = np.random.binomial(1, motion_prob)
        
        # Door: Peaks at morning/evening
        door_prob = np.where(
            (hour_of_day == 7) | (hour_of_day == 8) | 
            (hour_of_day == 17) | (hour_of_day == 18),
            0.2,
            0.02
        )
        door = np.random.binomial(1, door_prob)
        
        # Temperature: Varies with time of day
        temperature = 20 + 3 * np.sin(2 * np.pi * hour_of_day / 24) + np.random.normal(0, 0.5, n_samples)
        
        # Humidity: Inversely related to temperature
        humidity = 50 - 5 * np.sin(2 * np.pi * hour_of_day / 24) + np.random.normal(0, 2, n_samples)
        
        # Power: Higher during waking hours
        power_base = np.where(
            (hour_of_day >= 6) & (hour_of_day <= 23),
            500,
            100
        )
        power = power_base + np.random.exponential(100, n_samples)
        
        # Activity labels based on time of day
        activity_label = np.zeros(n_samples, dtype=int)
        for i, h in enumerate(hour_of_day):
            if 0 <= h < 6:
                activity_label[i] = 0  # sleeping
            elif 6 <= h < 8:
                activity_label[i] = 1  # waking
            elif h == 8:
                activity_label[i] = 2  # leaving
            elif 8 < h < 17:
                activity_label[i] = 6  # working (away)
            elif h == 17:
                activity_label[i] = 3  # arriving
            elif 17 < h < 19:
                activity_label[i] = 4  # cooking
            elif 19 <= h < 21:
                activity_label[i] = 5  # eating
            elif 21 <= h < 23:
                activity_label[i] = 7  # watching_tv
            else:
                activity_label[i] = 8  # relaxing
        
        # Add some noise to activity labels
        noise_mask = np.random.random(n_samples) < 0.1
        activity_label[noise_mask] = np.random.randint(0, 10, noise_mask.sum())
        
        df = pl.DataFrame({
            "timestamp": timestamps,
            "motion": motion,
            "door": door,
            "temperature": temperature,
            "humidity": humidity,
            "power": power,
            "activity_label": activity_label,
        })
        
        return df
    
    def create_sequences(
        self,
        df: pl.DataFrame,
        feature_cols: list[str] | None = None,
        label_col: str = "activity_label",
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Create sequences for LSTM training.
        
        Args:
            df: DataFrame with sensor data
            feature_cols: Columns to use as features
            label_col: Column containing activity labels
            
        Returns:
            Tuple of (X, y) where:
            - X: Shape (n_sequences, sequence_length, n_features)
            - y: Shape (n_sequences,)
        """
        if feature_cols is None:
            # Default feature columns
            feature_cols = [
                col for col in df.columns
                if col not in ["timestamp", "activity_label", "source_file", "house_id", "appliance"]
            ]
        
        logger.info(f"Creating sequences with features: {feature_cols}")
        
        # Sort by timestamp
        if "timestamp" in df.columns:
            df = df.sort("timestamp")
        
        # Extract feature matrix
        features = df.select(feature_cols).to_numpy()
        
        # Extract labels
        if label_col in df.columns:
            labels = df.select(label_col).to_numpy().flatten()
        else:
            labels = np.zeros(len(df), dtype=int)
        
        # Create sequences using sliding window
        n_samples = len(features)
        n_sequences = (n_samples - self.sequence_length) // self.step_size + 1
        
        X = np.zeros((n_sequences, self.sequence_length, len(feature_cols)))
        y = np.zeros(n_sequences, dtype=int)
        
        for i in range(n_sequences):
            start_idx = i * self.step_size
            end_idx = start_idx + self.sequence_length
            
            X[i] = features[start_idx:end_idx]
            y[i] = labels[end_idx - 1]  # Label is the last time step
        
        logger.info(f"Created {n_sequences:,} sequences of shape {X.shape}")
        
        return X, y
    
    def create_time_features(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Create time-based features from timestamp.
        
        Adds:
        - hour_of_day (0-23)
        - day_of_week (0-6)
        - is_weekend (0/1)
        - hour_sin, hour_cos (cyclical encoding)
        """
        if "timestamp" not in df.columns:
            return df
        
        df = df.with_columns([
            pl.col("timestamp").dt.hour().alias("hour_of_day"),
            pl.col("timestamp").dt.weekday().alias("day_of_week"),
            (pl.col("timestamp").dt.weekday() >= 5).cast(pl.Int32).alias("is_weekend"),
        ])
        
        # Cyclical encoding for hour
        df = df.with_columns([
            (np.sin(2 * np.pi * pl.col("hour_of_day") / 24)).alias("hour_sin"),
            (np.cos(2 * np.pi * pl.col("hour_of_day") / 24)).alias("hour_cos"),
        ])
        
        return df
    
    def normalize_features(
        self,
        df: pl.DataFrame,
        feature_cols: list[str],
    ) -> tuple[pl.DataFrame, dict[str, tuple[float, float]]]:
        """
        Normalize continuous features to [0, 1] range.
        
        Returns:
            Tuple of (normalized_df, normalization_params)
        """
        params = {}
        
        for col in feature_cols:
            if col in df.columns:
                min_val = df.select(pl.col(col).min()).item()
                max_val = df.select(pl.col(col).max()).item()
                
                if max_val > min_val:
                    df = df.with_columns([
                        ((pl.col(col) - min_val) / (max_val - min_val)).alias(col)
                    ])
                    params[col] = (min_val, max_val)
        
        return df, params
    
    def split_by_time(
        self,
        df: pl.DataFrame,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
    ) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
        """
        Split data chronologically (no data leakage).
        
        Args:
            df: DataFrame to split
            train_ratio: Ratio for training set
            val_ratio: Ratio for validation set
            
        Returns:
            Tuple of (train_df, val_df, test_df)
        """
        if "timestamp" in df.columns:
            df = df.sort("timestamp")
        
        n = len(df)
        train_end = int(n * train_ratio)
        val_end = int(n * (train_ratio + val_ratio))
        
        train_df = df[:train_end]
        val_df = df[train_end:val_end]
        test_df = df[val_end:]
        
        logger.info(
            f"Split data: train={len(train_df):,}, "
            f"val={len(val_df):,}, test={len(test_df):,}"
        )
        
        return train_df, val_df, test_df
    
    def get_activity_distribution(self, df: pl.DataFrame) -> pl.DataFrame:
        """Get distribution of activities in the dataset."""
        if "activity_label" not in df.columns:
            return pl.DataFrame()
        
        return (
            df
            .group_by("activity_label")
            .agg([
                pl.count().alias("count"),
            ])
            .sort("activity_label")
            .with_columns([
                pl.col("activity_label")
                .map_elements(lambda x: ACTIVITY_LABELS.get(x, "unknown"), return_dtype=pl.String)
                .alias("activity_name")
            ])
        )
    
    def save_processed(self, df: pl.DataFrame, output_path: Path) -> None:
        """Save processed data to Parquet."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        df.write_parquet(output_path)
        logger.info(f"Saved processed data to {output_path}")
    
    def load_processed(self, input_path: Path) -> pl.DataFrame:
        """Load previously processed data from Parquet."""
        return pl.read_parquet(input_path)


def main():
    """Example usage of SensorDataLoader."""
    logging.basicConfig(level=logging.INFO)
    
    loader = SensorDataLoader()
    
    # Load synthetic data (for testing)
    df = loader._create_synthetic_data(n_samples=5000)
    print(f"\nLoaded {len(df):,} samples")
    print(f"Columns: {df.columns}")
    print(f"\nSample data:\n{df.head()}")
    
    # Add time features
    df = loader.create_time_features(df)
    
    # Get activity distribution
    dist = loader.get_activity_distribution(df)
    print(f"\nActivity distribution:\n{dist}")
    
    # Create sequences
    X, y = loader.create_sequences(
        df,
        feature_cols=["motion", "door", "temperature", "humidity", "power"],
    )
    print(f"\nSequences shape: X={X.shape}, y={y.shape}")


if __name__ == "__main__":
    main()
