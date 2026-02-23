# data-collectors

Stateless data fetchers. Each service polls an external API on a schedule and writes to InfluxDB. Independently restartable, no cross-dependencies.

## Services

| Service | Port | External Source |
|---------|------|-----------------|
| weather-api | 8009 | OpenWeatherMap |
| smart-meter-service | 8014 | Home Assistant power entities |
| sports-api | 8005 | ESPN / HA Team Tracker |
| air-quality-service | 8012 | OpenWeatherMap AQI |
| carbon-intensity-service | 8010 | WattTime |
| electricity-pricing-service | 8011 | Energy pricing provider |
| calendar-service | 8013 | HA calendar entities |
| log-aggregator | 8015 | Docker socket / service logs |

## Depends On

core-platform (InfluxDB write, data-api metadata)

## Depended On By

ml-engine, automation-core, energy-analytics (indirect — via InfluxDB data)

## Compose

```bash
docker compose -f domains/data-collectors/compose.yml up -d
```
