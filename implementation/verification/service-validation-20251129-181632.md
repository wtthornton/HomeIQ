# Service Validation Report
Generated: Sat Nov 29 18:16:32 PST 2025

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
{"websocket-ingestion":{"name":"websocket-ingestion","status":"healthy","last_check":"2025-11-29T18:16:41.737716","response_time_ms":3.8899999999999997,"error_message":null},"ai-automation-service":{"name":"ai-automation-service","status":"healthy","last_check":"2025-11-29T18:16:41.740438","response_time_ms":2.37,"error_message":null},"influxdb":{"name":"influxdb","status":"pass","last_check":"2025-11-29T18:16:41.742206","response_time_ms":1.514,"error_message":null},"weather-api":{"name":"weather-api","status":"healthy","last_check":"2025-11-29T18:16:41.883027","response_time_ms":140.56199999999998,"error_message":null},"carbon-intensity-service":{"name":"carbon-intensity-service","status":"unhealthy","last_check":"2025-11-29T18:16:43.161363","response_time_ms":null,"error_message":"Cannot connect to host homeiq-carbon-intensity:8010 ssl:default [Name does not resolve]"},"electricity-pricing-service":{"name":"electricity-pricing-service","status":"unhealthy","last_check":"2025-11-29T18:16:44.423217","response_time_ms":null,"error_message":"Cannot connect to host homeiq-electricity-pricing:8011 ssl:default [Name does not resolve]"},"air-quality-service":{"name":"air-quality-service","status":"unhealthy","last_check":"2025-11-29T18:16:45.685998","response_time_ms":null,"error_message":"Cannot connect to host homeiq-air-quality:8012 ssl:default [Name does not resolve]"},"calendar-service":{"name":"calendar-service","status":"unhealthy","last_check":"2025-11-29T18:16:47.686287","response_time_ms":null,"error_message":"Timeout"},"smart-meter-service":{"name":"smart-meter-service","status":"healthy","last_check":"2025-11-29T18:16:47.690729","response_time_ms":4.208,"error_message":null}}
```
[0;34m[INFO][0m 1.2 Validating individual health endpoints...

### 1.2 Health Endpoint Validation

| Service | Port | Status | Response Time (ms) |
|---------|------|--------|-------------------|
[0;31m[✗ FAIL][0m data-retention (8080): Unhealthy or not responding
| data-retention | 8080 | ✗ Failed | - |
[0;32m[✓ PASS][0m ai-automation-service (8024): Healthy (10ms)
| ai-automation-service | 8024 | ✓ Healthy | 10 |
[0;32m[✓ PASS][0m ha-setup-service (8027): Healthy (8ms)
| ha-setup-service | 8027 | ✓ Healthy | 8 |
[0;32m[✓ PASS][0m ai-training-service (8033): Healthy (11ms)
| ai-training-service | 8033 | ✓ Healthy | 11 |
[0;32m[✓ PASS][0m device-database-client (8022): Healthy (9ms)
| device-database-client | 8022 | ✓ Healthy | 9 |
[0;31m[✗ FAIL][0m carbon-intensity (8010): Unhealthy or not responding
| carbon-intensity | 8010 | ✗ Failed | - |
[0;32m[✓ PASS][0m ml-service (8025): Healthy (10ms)
| ml-service | 8025 | ✓ Healthy | 10 |
[0;32m[✓ PASS][0m device-setup-assistant (8021): Healthy (8ms)
| device-setup-assistant | 8021 | ✓ Healthy | 8 |
[0;32m[✓ PASS][0m openai-service (8020): Healthy (10ms)
| openai-service | 8020 | ✓ Healthy | 10 |
[0;32m[✓ PASS][0m device-recommender (8023): Healthy (10ms)
| device-recommender | 8023 | ✓ Healthy | 10 |
[0;32m[✓ PASS][0m ai-code-executor (8030): Healthy (7ms)
| ai-code-executor | 8030 | ✓ Healthy | 7 |
[0;32m[✓ PASS][0m openvino-service (8026): Healthy (8ms)
| openvino-service | 8026 | ✓ Healthy | 8 |
[0;32m[✓ PASS][0m ai-core-service (8018): Healthy (17ms)
| ai-core-service | 8018 | ✓ Healthy | 17 |
[0;31m[✗ FAIL][0m weather-api (8009): Unhealthy or not responding
| weather-api | 8009 | ✗ Failed | - |
[0;32m[✓ PASS][0m data-api (8006): Healthy (13ms)
| data-api | 8006 | ✓ Healthy | 13 |
[0;32m[✓ PASS][0m device-intelligence-service (8028): Healthy (11ms)
| device-intelligence-service | 8028 | ✓ Healthy | 11 |
[0;32m[✓ PASS][0m log-aggregator (8015): Healthy (12ms)
| log-aggregator | 8015 | ✓ Healthy | 12 |
[0;31m[✗ FAIL][0m electricity-pricing (8011): Unhealthy or not responding
| electricity-pricing | 8011 | ✗ Failed | - |
[0;32m[✓ PASS][0m energy-correlator (8017): Healthy (9ms)
| energy-correlator | 8017 | ✓ Healthy | 9 |
[0;32m[✓ PASS][0m device-health-monitor (8019): Healthy (9ms)
| device-health-monitor | 8019 | ✓ Healthy | 9 |
[0;32m[✓ PASS][0m websocket-ingestion (8001): Healthy (8ms)
| websocket-ingestion | 8001 | ✓ Healthy | 8 |
[0;31m[✗ FAIL][0m ai-pattern-service (8034): Unhealthy or not responding
| ai-pattern-service | 8034 | ✗ Failed | - |
[0;32m[✓ PASS][0m health-dashboard (3000): Healthy (13ms)
| health-dashboard | 3000 | ✓ Healthy | 13 |
[0;32m[✓ PASS][0m admin-api (8003): Healthy (10ms)
| admin-api | 8003 | ✓ Healthy | 10 |
[0;32m[✓ PASS][0m smart-meter (8014): Healthy (8ms)
| smart-meter | 8014 | ✓ Healthy | 8 |
[0;32m[✓ PASS][0m device-context-classifier (8032): Healthy (9ms)
| device-context-classifier | 8032 | ✓ Healthy | 9 |
[0;32m[✓ PASS][0m ner-service (8031): Healthy (11ms)
| ner-service | 8031 | ✓ Healthy | 11 |
[0;31m[✗ FAIL][0m air-quality (8012): Unhealthy or not responding
| air-quality | 8012 | ✗ Failed | - |
[0;32m[✓ PASS][0m influxdb (8086): Healthy (13ms)
| influxdb | 8086 | ✓ Healthy | 13 |
[0;32m[✓ PASS][0m automation-miner (8029): Healthy (23ms)
| automation-miner | 8029 | ✓ Healthy | 23 |
[0;31m[✗ FAIL][0m ai-query-service (8035): Unhealthy or not responding
| ai-query-service | 8035 | ✗ Failed | - |
[0;32m[✓ PASS][0m ai-automation-ui (3001): Healthy (7ms)
| ai-automation-ui | 3001 | ✓ Healthy | 7 |
[0;34m[INFO][0m 1.3 Validating service dependencies...

### 1.3 Service Dependencies Validation

[0;32m[✓ PASS][0m Dependency health check endpoint accessible
```json
{"influxdb":{"status":"healthy","last_check":"2025-11-29T18:16:50.283702","response_time_ms":"N/A"},"weather_api":{"status":"healthy","last_check":"2025-11-29T18:16:50.419839","response_time_ms":"N/A"}}
```
[0;34m[INFO][0m 1.4 Checking resource usage...

### 1.4 Resource Usage Check

[0;32m[✓ PASS][0m Resource usage captured
Resource usage details saved to: `implementation/verification/resource-usage-20251129-181650.txt`
[1;33m[⚠ WARN][0m Some containers have high memory usage:

**Warning:** High memory usage detected:
18edb48b0e22 151.3MiB
61773adb912b 164.6MiB
57c5629d3437 109.9MiB
ca6b7af6871f 537.7MiB
5bbfd50f81cf 135.8MiB
c38fbdecf6fa 223.8MiB
f013f1c6a852 117.4MiB
42be3518d3e4 314.9MiB

## Summary

- **Total Services Checked:** 32
- **Healthy Services:** 25
- **Failed Services:** 7
- **Success Rate:** 78.1%

**Status:** ❌ Some validations failed
[0;31m[✗ FAIL][0m Phase 1 validation complete - Some issues found
