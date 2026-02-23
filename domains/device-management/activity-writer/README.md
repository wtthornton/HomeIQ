# Activity Writer Service

Epic Activity Recognition Integration Phase 1 - Story 1.1

Periodically fetches state_changed events, builds feature windows, calls activity-recognition for prediction, and writes results to InfluxDB.

## Features

- **Configurable scheduler**: Runs every 5–15 minutes (default: 5 min via `ACTIVITY_WRITER_INTERVAL_SECONDS`)
- **Event sourcing**: Fetches from data-api (with auth) or InfluxDB direct for state values
- **Feature extraction**: 1-min buckets with motion, door, temperature, humidity, power
- **Activity prediction**: POST to activity-recognition service (min 10 readings)
- **InfluxDB write**: Point with measurement `home_activity`, tags `home_id`, fields `activity`, `activity_id`, `confidence`
- **Retry**: Tenacity for activity-recognition and InfluxDB calls
- **Health/metrics**: `last_successful_run`, `last_error`, `cycles_succeeded`, `cycles_failed`

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVICE_PORT` | 8035 | HTTP port |
| `ACTIVITY_WRITER_INTERVAL_SECONDS` | 300 | Scheduler interval (5 min) |
| `DATA_API_URL` | http://data-api:8006 | Data API base URL |
| `DATA_API_API_KEY` | - | API key for data-api auth |
| `ACTIVITY_RECOGNITION_URL` | http://activity-recognition:8036 | Activity recognition service |
| `ACTIVITY_RECOGNITION_TIMEOUT` | 30 | Timeout in seconds |
| `INFLUXDB_URL` | http://influxdb:8086 | InfluxDB URL |
| `INFLUXDB_TOKEN` | - | InfluxDB token (required) |
| `INFLUXDB_ORG` | homeiq | InfluxDB org |
| `INFLUXDB_BUCKET` | home_assistant_events | Bucket for home_activity |
| `HOME_ID` | default | Home identifier tag |

## Endpoints

- `GET /` - Service info
- `GET /health` - Health check (includes last_successful_run, cycles)
- `GET /metrics` - last_successful_run, last_error, cycles_succeeded, cycles_failed

## Docker

```bash
docker-compose build activity-writer
docker-compose up -d activity-writer
```

## Dependencies

- data-api (events endpoint)
- activity-recognition (predict endpoint)
- InfluxDB
