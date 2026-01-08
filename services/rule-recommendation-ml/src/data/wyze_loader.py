"""
Wyze Rule Recommendation Dataset Loader

Loads and preprocesses the Wyze Rule Recommendation dataset from Hugging Face
for training rule recommendation models. Uses Polars for high-performance
data processing (10-100x faster than Pandas).

Dataset: wyzelabs/RuleRecommendation
- 1M+ real automation rules from 300K+ users
- Contains triggers, actions, device types, temporal patterns
"""

import logging
from pathlib import Path
from typing import Any

import polars as pl

logger = logging.getLogger(__name__)


# Wyze device type to Home Assistant domain mapping
WYZE_TO_HA_DOMAIN_MAPPING: dict[str, str] = {
    # Lighting
    "light": "light",
    "bulb": "light",
    "lightstrip": "light",
    "lamp": "light",
    
    # Switches and plugs
    "plug": "switch",
    "switch": "switch",
    "outlet": "switch",
    
    # Cameras and security
    "camera": "camera",
    "cam": "camera",
    "doorbell": "camera",
    
    # Sensors
    "sensor": "binary_sensor",
    "motion_sensor": "binary_sensor",
    "contact_sensor": "binary_sensor",
    "door_sensor": "binary_sensor",
    "window_sensor": "binary_sensor",
    "leak_sensor": "binary_sensor",
    
    # Climate
    "thermostat": "climate",
    "hvac": "climate",
    "fan": "fan",
    
    # Security
    "lock": "lock",
    "doorlock": "lock",
    "alarm": "alarm_control_panel",
    
    # Other
    "vacuum": "vacuum",
    "robot_vacuum": "vacuum",
    "sprinkler": "valve",
    "garage": "cover",
    "garage_door": "cover",
    "blind": "cover",
    "shade": "cover",
}

# Wyze action to Home Assistant service mapping
WYZE_TO_HA_ACTION_MAPPING: dict[str, str] = {
    "turn_on": "turn_on",
    "turn_off": "turn_off",
    "toggle": "toggle",
    "set_brightness": "turn_on",  # with brightness parameter
    "set_color": "turn_on",  # with rgb_color parameter
    "lock": "lock",
    "unlock": "unlock",
    "arm": "arm_away",
    "disarm": "disarm",
    "set_temperature": "set_temperature",
    "set_hvac_mode": "set_hvac_mode",
}

# Wyze trigger to Home Assistant trigger platform mapping
WYZE_TO_HA_TRIGGER_MAPPING: dict[str, str] = {
    "motion_detected": "state",  # binary_sensor motion
    "door_opened": "state",
    "door_closed": "state",
    "sunrise": "sun",
    "sunset": "sun",
    "time": "time",
    "schedule": "time",
    "device_on": "state",
    "device_off": "state",
    "temperature_above": "numeric_state",
    "temperature_below": "numeric_state",
    "humidity_above": "numeric_state",
    "humidity_below": "numeric_state",
}


class WyzeDataLoader:
    """
    Load and preprocess Wyze Rule Recommendation dataset using Polars.
    
    This loader:
    1. Streams the dataset from Hugging Face to avoid memory issues
    2. Maps Wyze device types to Home Assistant domains
    3. Extracts trigger-action patterns with frequency counts
    4. Prepares data for collaborative filtering model training
    """
    
    def __init__(
        self,
        cache_dir: Path | None = None,
        streaming: bool = True,
    ):
        """
        Initialize the Wyze data loader.
        
        Args:
            cache_dir: Directory to cache downloaded data
            streaming: Whether to stream dataset (recommended for large data)
        """
        self.cache_dir = cache_dir or Path("./data/wyze_cache")
        self.streaming = streaming
        self._dataset = None
        
    def load(self) -> pl.DataFrame:
        """
        Load and preprocess the Wyze Rule Recommendation dataset.
        
        Returns:
            Polars DataFrame with preprocessed rule data including:
            - user_id: Anonymized user identifier
            - rule_id: Unique rule identifier
            - trigger_device_type: Original Wyze trigger device type
            - trigger_ha_domain: Mapped Home Assistant domain
            - action_device_type: Original Wyze action device type
            - action_ha_domain: Mapped Home Assistant domain
            - trigger_type: Type of trigger (motion, time, state, etc.)
            - action_type: Type of action (turn_on, turn_off, etc.)
            - ha_trigger_platform: Home Assistant trigger platform
            - ha_service: Home Assistant service to call
        """
        try:
            from datasets import load_dataset
        except ImportError:
            raise ImportError(
                "Please install the datasets library: pip install datasets>=3.0.0"
            )
        
        logger.info("Loading Wyze Rule Recommendation dataset from Hugging Face...")
        
        # Load dataset with streaming for memory efficiency
        dataset = load_dataset(
            "wyzelabs/RuleRecommendation",
            streaming=self.streaming,
            cache_dir=str(self.cache_dir),
        )
        
        self._dataset = dataset
        
        # Convert to Polars DataFrame
        if self.streaming:
            # For streaming, we need to iterate and collect
            logger.info("Streaming dataset - collecting data...")
            records = []
            for i, record in enumerate(dataset["train"]):
                records.append(record)
                if i > 0 and i % 100000 == 0:
                    logger.info(f"Processed {i:,} records...")
                # Limit for initial testing - remove in production
                if i >= 1000000:  # 1M records max
                    break
            df = pl.DataFrame(records)
        else:
            # Non-streaming: convert directly
            df = pl.from_arrow(dataset["train"].data.table)
        
        logger.info(f"Loaded {len(df):,} rules from Wyze dataset")
        
        # Preprocess and map to Home Assistant domains
        df = self._preprocess(df)
        
        return df
    
    def _preprocess(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Preprocess the raw Wyze data and map to Home Assistant domains.
        
        Args:
            df: Raw Polars DataFrame from Wyze dataset
            
        Returns:
            Preprocessed DataFrame with HA mappings
        """
        logger.info("Preprocessing Wyze data and mapping to Home Assistant domains...")
        
        # Get column names to handle different dataset versions
        columns = df.columns
        
        # Identify trigger and action device type columns
        trigger_col = self._find_column(columns, ["trigger_device", "trigger_type", "trigger"])
        action_col = self._find_column(columns, ["action_device", "action_type", "action"])
        user_col = self._find_column(columns, ["user_id", "user", "uid"])
        rule_col = self._find_column(columns, ["rule_id", "rule", "id"])
        
        # Build preprocessing expressions
        expressions = []
        
        # Map trigger device types to HA domains
        if trigger_col:
            expressions.append(
                pl.col(trigger_col)
                .str.to_lowercase()
                .replace(WYZE_TO_HA_DOMAIN_MAPPING, default="unknown")
                .alias("trigger_ha_domain")
            )
            expressions.append(
                pl.col(trigger_col).alias("trigger_device_type")
            )
        
        # Map action device types to HA domains
        if action_col:
            expressions.append(
                pl.col(action_col)
                .str.to_lowercase()
                .replace(WYZE_TO_HA_DOMAIN_MAPPING, default="unknown")
                .alias("action_ha_domain")
            )
            expressions.append(
                pl.col(action_col).alias("action_device_type")
            )
        
        # Preserve user and rule IDs
        if user_col:
            expressions.append(pl.col(user_col).alias("user_id"))
        if rule_col:
            expressions.append(pl.col(rule_col).alias("rule_id"))
        
        # Apply transformations
        if expressions:
            df = df.with_columns(expressions)
        
        # Add rule pattern identifier (trigger_domain -> action_domain)
        if "trigger_ha_domain" in df.columns and "action_ha_domain" in df.columns:
            df = df.with_columns([
                (pl.col("trigger_ha_domain") + "_to_" + pl.col("action_ha_domain"))
                .alias("rule_pattern")
            ])
        
        logger.info(f"Preprocessed {len(df):,} rules with {len(df.columns)} columns")
        
        return df
    
    def _find_column(self, columns: list[str], candidates: list[str]) -> str | None:
        """Find a column by checking multiple candidate names."""
        for candidate in candidates:
            for col in columns:
                if candidate.lower() in col.lower():
                    return col
        return None
    
    def get_rule_patterns(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Extract unique rule patterns with frequency counts.
        
        Args:
            df: Preprocessed Wyze DataFrame
            
        Returns:
            DataFrame with pattern frequencies
        """
        if "rule_pattern" not in df.columns:
            raise ValueError("DataFrame must have 'rule_pattern' column")
        
        patterns = (
            df
            .group_by("rule_pattern")
            .agg([
                pl.count().alias("frequency"),
                pl.col("user_id").n_unique().alias("unique_users"),
            ])
            .sort("frequency", descending=True)
        )
        
        logger.info(f"Found {len(patterns):,} unique rule patterns")
        
        return patterns
    
    def get_user_rule_matrix(self, df: pl.DataFrame) -> tuple[Any, dict[int, str], dict[int, str]]:
        """
        Create user-rule interaction matrix for collaborative filtering.
        
        Args:
            df: Preprocessed Wyze DataFrame
            
        Returns:
            Tuple of:
            - Sparse CSR matrix of user-rule interactions
            - User ID to index mapping
            - Rule pattern to index mapping
        """
        from scipy.sparse import csr_matrix
        import numpy as np
        
        if "user_id" not in df.columns or "rule_pattern" not in df.columns:
            raise ValueError("DataFrame must have 'user_id' and 'rule_pattern' columns")
        
        # Create mappings
        users = df.select("user_id").unique().to_series().to_list()
        patterns = df.select("rule_pattern").unique().to_series().to_list()
        
        user_to_idx = {user: idx for idx, user in enumerate(users)}
        pattern_to_idx = {pattern: idx for idx, pattern in enumerate(patterns)}
        idx_to_user = {idx: user for user, idx in user_to_idx.items()}
        idx_to_pattern = {idx: pattern for pattern, idx in pattern_to_idx.items()}
        
        # Create sparse matrix
        user_indices = df.select("user_id").to_series().map_elements(
            lambda x: user_to_idx.get(x, 0), return_dtype=pl.Int64
        ).to_numpy()
        pattern_indices = df.select("rule_pattern").to_series().map_elements(
            lambda x: pattern_to_idx.get(x, 0), return_dtype=pl.Int64
        ).to_numpy()
        
        # Binary interaction (1 if user has rule, 0 otherwise)
        data = np.ones(len(df))
        
        matrix = csr_matrix(
            (data, (user_indices, pattern_indices)),
            shape=(len(users), len(patterns))
        )
        
        logger.info(
            f"Created user-rule matrix: {matrix.shape[0]:,} users x {matrix.shape[1]:,} patterns"
        )
        
        return matrix, idx_to_user, idx_to_pattern
    
    def save_processed(self, df: pl.DataFrame, output_path: Path) -> None:
        """Save processed data to Parquet for fast loading."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        df.write_parquet(output_path)
        logger.info(f"Saved processed data to {output_path}")
    
    def load_processed(self, input_path: Path) -> pl.DataFrame:
        """Load previously processed data from Parquet."""
        return pl.read_parquet(input_path)


def main():
    """Example usage of WyzeDataLoader."""
    logging.basicConfig(level=logging.INFO)
    
    loader = WyzeDataLoader(streaming=True)
    
    # Load and preprocess
    df = loader.load()
    print(f"\nLoaded {len(df):,} rules")
    print(f"Columns: {df.columns}")
    print(f"\nSample data:\n{df.head()}")
    
    # Get pattern frequencies
    patterns = loader.get_rule_patterns(df)
    print(f"\nTop 10 rule patterns:\n{patterns.head(10)}")
    
    # Create user-rule matrix
    matrix, idx_to_user, idx_to_pattern = loader.get_user_rule_matrix(df)
    print(f"\nUser-rule matrix shape: {matrix.shape}")
    print(f"Non-zero entries: {matrix.nnz:,}")


if __name__ == "__main__":
    main()
