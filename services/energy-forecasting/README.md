# Energy Forecasting Service

ML-powered energy consumption forecasting for HomeIQ.

## Overview

This service provides energy consumption forecasting using modern time series models:
- **N-HiTS**: Fast neural forecasting
- **TFT**: Temporal Fusion Transformer for interpretability
- **Statistical baselines**: ARIMA, Prophet

## Features

- **Forecasting**: Predict energy consumption up to 7 days ahead
- **Peak Prediction**: Identify peak usage hours
- **Optimization**: Recommend best hours for high-power activities

## Port

- **Internal**: 8037
- **External**: 8037

## API Endpoints

### Health & Info

- `GET /api/v1/health` - Health check
- `GET /api/v1/model/info` - Model information

### Forecasting

- `GET /api/v1/forecast?hours=48` - Get energy forecast
- `GET /api/v1/peak-prediction` - Predict peak usage
- `GET /api/v1/optimization` - Get optimization recommendations

## Training

```python
from src.data.energy_loader import EnergyDataLoader
from src.models.energy_forecaster import EnergyForecaster

# Load data
loader = EnergyDataLoader()
df = loader.load_from_influxdb()

# Convert to Darts TimeSeries
series = loader.to_darts_timeseries(df)

# Split
train, test = series.split_after(0.8)

# Train model
forecaster = EnergyForecaster(
    model_type="nhits",
    input_chunk_length=168,  # 1 week
    output_chunk_length=48,  # 2 days
)
forecaster.fit(train)

# Evaluate
metrics = forecaster.evaluate(test)
print(f"MAPE: {metrics['mape']:.2%}")

# Save
forecaster.save("models/energy_forecaster")
```

## Docker

```bash
docker build -t homeiq-energy-forecasting .
docker run -p 8037:8037 -v ./models:/app/models homeiq-energy-forecasting
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8037` | Service port |
| `MODEL_PATH` | `./models/energy_forecaster` | Model path |
| `INFLUXDB_URL` | `http://localhost:8086` | InfluxDB URL |
| `INFLUXDB_TOKEN` | - | InfluxDB token |
| `INFLUXDB_ORG` | `homeiq` | InfluxDB organization |
