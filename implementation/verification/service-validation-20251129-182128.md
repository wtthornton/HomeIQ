# Service Validation Report
Generated: Sat Nov 29 18:21:28 PST 2025

## Phase 1: Docker Service Validation

[0;34m[INFO][0m Starting Phase 1: Docker Service Validation...
[0;34m[INFO][0m 1.1 Checking container status...

### 1.1 Container Status Check

[0;34m[INFO][0m Found 27 containers
**Total Containers:** 27

| Container Name | Status | Ports |
|----------------|--------|-------|
[0;32m[✓ PASS][0m Container homeiq-dashboard: Up 5 hours (healthy)
| homeiq-dashboard | Up 5 hours (healthy) | 0.0.0.0:3000->80/tcp, [::]:3000->80/tcp |
[0;32m[✓ PASS][0m Container homeiq-admin: Up 5 hours (healthy)
| homeiq-admin | Up 5 hours (healthy) | 0.0.0.0:8003->8004/tcp, [::]:8003->8004/tcp |
[0;32m[✓ PASS][0m Container homeiq-websocket: Up 5 hours (healthy)
| homeiq-websocket | Up 5 hours (healthy) | 0.0.0.0:8001->8001/tcp, [::]:8001->8001/tcp |
[0;32m[✓ PASS][0m Container ai-query-service: Up 6 hours (healthy)
| ai-query-service | Up 6 hours (healthy) | 0.0.0.0:8035->8018/tcp, [::]:8035->8018/tcp |
[0;32m[✓ PASS][0m Container homeiq-device-intelligence: Up 6 hours (healthy)
| homeiq-device-intelligence | Up 6 hours (healthy) | 0.0.0.0:8028->8019/tcp, [::]:8028->8019/tcp |
[0;32m[✓ PASS][0m Container homeiq-influxdb: Up 6 hours (healthy)
| homeiq-influxdb | Up 6 hours (healthy) | 0.0.0.0:8086->8086/tcp, [::]:8086->8086/tcp |
[0;32m[✓ PASS][0m Container homeiq-data-api: Up 6 hours (healthy)
| homeiq-data-api | Up 6 hours (healthy) | 0.0.0.0:8006->8006/tcp, [::]:8006->8006/tcp |
[0;32m[✓ PASS][0m Container homeiq-setup-service: Up 6 hours (healthy)
| homeiq-setup-service | Up 6 hours (healthy) | 0.0.0.0:8027->8020/tcp, [::]:8027->8020/tcp |
[0;32m[✓ PASS][0m Container ai-code-executor: Up 6 hours (healthy)
| ai-code-executor | Up 6 hours (healthy) | 0.0.0.0:8030->8030/tcp, [::]:8030->8030/tcp |
[0;32m[✓ PASS][0m Container ai-automation-ui: Up 6 hours (healthy)
| ai-automation-ui | Up 6 hours (healthy) | 0.0.0.0:3001->80/tcp, [::]:3001->80/tcp |
[0;32m[✓ PASS][0m Container ai-automation-service: Up 6 hours (healthy)
| ai-automation-service | Up 6 hours (healthy) | 0.0.0.0:8024->8018/tcp, [::]:8024->8018/tcp |
[0;32m[✓ PASS][0m Container ai-pattern-service: Up 6 hours
| ai-pattern-service | Up 6 hours | 0.0.0.0:8034->8020/tcp, [::]:8034->8020/tcp |
[0;32m[✓ PASS][0m Container homeiq-energy-correlator: Up 6 hours (healthy)
| homeiq-energy-correlator | Up 6 hours (healthy) | 0.0.0.0:8017->8017/tcp, [::]:8017->8017/tcp |
[0;32m[✓ PASS][0m Container homeiq-smart-meter: Up 6 hours (healthy)
| homeiq-smart-meter | Up 6 hours (healthy) | 0.0.0.0:8014->8014/tcp, [::]:8014->8014/tcp |
[0;32m[✓ PASS][0m Container homeiq-ai-core-service: Up 6 hours (healthy)
| homeiq-ai-core-service | Up 6 hours (healthy) | 0.0.0.0:8018->8018/tcp, [::]:8018->8018/tcp |
[0;32m[✓ PASS][0m Container ai-training-service: Up 6 hours (healthy)
| ai-training-service | Up 6 hours (healthy) | 0.0.0.0:8033->8022/tcp, [::]:8033->8022/tcp |
[0;32m[✓ PASS][0m Container homeiq-device-health-monitor: Up 6 hours (healthy)
| homeiq-device-health-monitor | Up 6 hours (healthy) | 0.0.0.0:8019->8019/tcp, [::]:8019->8019/tcp |
[0;32m[✓ PASS][0m Container homeiq-ner-service: Up 6 hours (healthy)
| homeiq-ner-service | Up 6 hours (healthy) | 0.0.0.0:8031->8031/tcp, [::]:8031->8031/tcp |
[0;32m[✓ PASS][0m Container homeiq-log-aggregator: Up 6 hours (healthy)
| homeiq-log-aggregator | Up 6 hours (healthy) | 0.0.0.0:8015->8015/tcp, [::]:8015->8015/tcp |
[0;32m[✓ PASS][0m Container homeiq-ml-service: Up 6 hours (healthy)
| homeiq-ml-service | Up 6 hours (healthy) | 0.0.0.0:8025->8020/tcp, [::]:8025->8020/tcp |
[0;32m[✓ PASS][0m Container homeiq-openai-service: Up 6 hours (healthy)
| homeiq-openai-service | Up 6 hours (healthy) | 0.0.0.0:8020->8020/tcp, [::]:8020->8020/tcp |
[0;32m[✓ PASS][0m Container homeiq-device-setup-assistant: Up 6 hours (healthy)
| homeiq-device-setup-assistant | Up 6 hours (healthy) | 0.0.0.0:8021->8021/tcp, [::]:8021->8021/tcp |
[0;32m[✓ PASS][0m Container homeiq-openvino-service: Up 6 hours (healthy)
| homeiq-openvino-service | Up 6 hours (healthy) | 0.0.0.0:8026->8019/tcp, [::]:8026->8019/tcp |
[0;32m[✓ PASS][0m Container automation-miner: Up 6 hours (healthy)
| automation-miner | Up 6 hours (healthy) | 0.0.0.0:8029->8019/tcp, [::]:8029->8019/tcp |
[0;32m[✓ PASS][0m Container homeiq-device-database-client: Up 6 hours (healthy)
| homeiq-device-database-client | Up 6 hours (healthy) | 0.0.0.0:8022->8022/tcp, [::]:8022->8022/tcp |
[0;32m[✓ PASS][0m Container homeiq-device-context-classifier: Up 6 hours (healthy)
| homeiq-device-context-classifier | Up 6 hours (healthy) | 0.0.0.0:8032->8020/tcp, [::]:8032->8020/tcp |
[0;32m[✓ PASS][0m Container homeiq-device-recommender: Up 6 hours (healthy)
| homeiq-device-recommender | Up 6 hours (healthy) | 0.0.0.0:8023->8023/tcp, [::]:8023->8023/tcp |
[0;34m[INFO][0m 1.1.2 Checking service health via admin-api...
[0;32m[✓ PASS][0m Admin API health endpoint accessible

### Service Health Status (from Admin API)

```json
{"websocket-ingestion":{"name":"websocket-ingestion","status":"healthy","last_check":"2025-11-29T18:21:39.311298","response_time_ms":1.8259999999999998,"error_message":null},"ai-automation-service":{"name":"ai-automation-service","status":"unhealthy","last_check":"2025-11-29T18:21:41.311727","response_time_ms":null,"error_message":"Timeout"},"influxdb":{"name":"influxdb","status":"pass","last_check":"2025-11-29T18:21:41.313770","response_time_ms":1.9009999999999998,"error_message":null},"weather-api":{"name":"weather-api","status":"healthy","last_check":"2025-11-29T18:21:41.440474","response_time_ms":126.49499999999999,"error_message":null},"carbon-intensity-service":{"name":"carbon-intensity-service","status":"unhealthy","last_check":"2025-11-29T18:21:42.712863","response_time_ms":null,"error_message":"Cannot connect to host homeiq-carbon-intensity:8010 ssl:default [Name does not resolve]"},"electricity-pricing-service":{"name":"electricity-pricing-service","status":"unhealthy","last_check":"2025-11-29T18:21:43.970825","response_time_ms":null,"error_message":"Cannot connect to host homeiq-electricity-pricing:8011 ssl:default [Name does not resolve]"},"air-quality-service":{"name":"air-quality-service","status":"unhealthy","last_check":"2025-11-29T18:21:45.234246","response_time_ms":null,"error_message":"Cannot connect to host homeiq-air-quality:8012 ssl:default [Name does not resolve]"},"calendar-service":{"name":"calendar-service","status":"unhealthy","last_check":"2025-11-29T18:21:47.235291","response_time_ms":null,"error_message":"Timeout"},"smart-meter-service":{"name":"smart-meter-service","status":"healthy","last_check":"2025-11-29T18:21:47.238290","response_time_ms":2.801,"error_message":null}}
```
[0;34m[INFO][0m 1.2 Validating individual health endpoints...

### 1.2 Health Endpoint Validation

| Service | Port | Status | Response Time (ms) | Type |
|---------|------|--------|-------------------|------|
[0;32m[✓ PASS][0m ai-automation-service (8024): Healthy (175586ms)
| ai-automation-service | 8024 | ✓ Healthy | 175586 | Required |
[0;32m[✓ PASS][0m ha-setup-service (8027): Healthy (9ms)
| ha-setup-service | 8027 | ✓ Healthy | 9 | Required |
[0;32m[✓ PASS][0m ai-training-service (8033): Healthy (12ms)
| ai-training-service | 8033 | ✓ Healthy | 12 | Required |
[0;32m[✓ PASS][0m device-database-client (8022): Healthy (11ms)
| device-database-client | 8022 | ✓ Healthy | 11 | Required |
[0;32m[✓ PASS][0m ml-service (8025): Healthy (11ms)
| ml-service | 8025 | ✓ Healthy | 11 | Required |
[0;32m[✓ PASS][0m device-setup-assistant (8021): Healthy (10ms)
| device-setup-assistant | 8021 | ✓ Healthy | 10 | Required |
[0;32m[✓ PASS][0m openai-service (8020): Healthy (12ms)
| openai-service | 8020 | ✓ Healthy | 12 | Required |
[0;32m[✓ PASS][0m device-recommender (8023): Healthy (11ms)
| device-recommender | 8023 | ✓ Healthy | 11 | Required |
[0;32m[✓ PASS][0m ai-code-executor (8030): Healthy (11ms)
