"""Example usage of the EnergyDataLoader."""

import logging


def main():
    """Example usage."""
    logging.basicConfig(level=logging.INFO)

    from src.data.energy_loader import EnergyDataLoader

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
