"""Example usage of the EnergyForecaster model."""

import logging

import numpy as np


def main():
    """Example usage."""
    logging.basicConfig(level=logging.INFO)

    try:
        from darts import TimeSeries
        import pandas as pd
    except ImportError:
        print("Darts not installed. Install with: pip install darts>=0.30.0")
        return

    from src.models.energy_forecaster import EnergyForecaster

    # Create synthetic data
    np.random.seed(42)
    n_samples = 24 * 30  # 30 days of hourly data

    timestamps = pd.date_range(start="2024-01-01", periods=n_samples, freq="h")
    hour = timestamps.hour

    # Generate energy pattern
    values = 200 + 100 * np.sin(2 * np.pi * hour / 24) + np.random.normal(0, 20, n_samples)

    df = pd.DataFrame({"timestamp": timestamps, "power": values})

    # Create TimeSeries
    series = TimeSeries.from_dataframe(df, time_col="timestamp", value_cols="power")

    # Split
    train, test = series.split_after(0.8)

    print(f"Train: {len(train)}, Test: {len(test)}")

    # Train model
    forecaster = EnergyForecaster(
        model_type="naive",  # Use naive for quick testing
        input_chunk_length=24,
        output_chunk_length=24,
    )

    forecaster.fit(train)

    # Evaluate
    metrics = forecaster.evaluate(test)
    print(f"\nMetrics: {metrics}")

    # Forecast
    forecast = forecaster.predict(n=24)
    print(f"\nForecast shape: {forecast.values().shape}")


if __name__ == "__main__":
    main()
