# Home Assistant WebSocket Call Tree Documentation

## Overview

This document provides a comprehensive call tree analysis of the Home Assistant WebSocket event processing system, tracing the complete lifecycle from WebSocket connection establishment to final event storage and processing completion.

## System Architecture

The HA-Ingestor system consists of multiple interconnected services:

- **WebSocket Ingestion Service** - Primary event ingestion from Home Assistant
- **Enrichment Pipeline Service** - Event processing, normalization, and storage
- **Weather API Integration** - External weather data enrichment
- **InfluxDB Storage** - Time-series data persistence

## Complete Call Tree

### 1. Service Initialization and Startup

```
main() [services/websocket-ingestion/src/main.py:499]
├── create_app() [services/websocket-ingestion/src/main.py:478]
│   ├── WebSocketIngestionService.__init__() [services/websocket-ingestion/src/main.py:45]
│   │   ├── HealthCheckHandler() [services/websocket-ingestion/src/health_check.py]
│   │   ├── Environment variable loading [services/websocket-ingestion/src/main.py:62-79]
│   │   └── Configuration validation [services/websocket-ingestion/src/main.py:81-82]
│   ├── web.Application() [aiohttp framework]
│   ├── create_correlation_middleware() [shared/correlation_middleware.py]
│   ├── app.router.add_get('/health', service.health_handler.handle)
│   └── app.router.add_get('/ws', websocket_handler)
├── SimpleHTTPClient.__aenter__() [services/websocket-ingestion/src/http_client.py:13]
│   └── aiohttp.ClientSession() [aiohttp framework]
├── web.AppRunner(app).setup() [aiohttp framework]
├── web.TCPSite(runner, '0.0.0.0', port).start() [aiohttp framework]
└── service.start() [services/websocket-ingestion/src/main.py:85]
    ├── generate_correlation_id() [shared/logging_config.py]
    ├── set_correlation_id(corr_id) [shared/logging_config.py]
    ├── MemoryManager(max_memory_mb) [services/websocket-ingestion/src/memory_manager.py]
    ├── EventQueue(maxsize=10000) [services/websocket-ingestion/src/event_queue.py:17]
    ├── BatchProcessor(batch_size, batch_timeout) [services/websocket-ingestion/src/batch_processor.py:18]
    ├── AsyncEventProcessor(max_workers, processing_rate_limit) [services/websocket-ingestion/src/async_event_processor.py:15]
    ├── memory_manager.start() [services/websocket-ingestion/src/memory_manager.py]
    ├── batch_processor.start() [services/websocket-ingestion/src/batch_processor.py:56]
    │   └── asyncio.create_task(_processing_loop()) [services/websocket-ingestion/src/batch_processor.py:66]
    ├── async_event_processor.start() [services/websocket-ingestion/src/async_event_processor.py:45]
    │   └── asyncio.create_task(_worker()) for each worker [services/websocket-ingestion/src/async_event_processor.py:55]
    ├── WeatherEnrichmentService() [services/websocket-ingestion/src/weather_enrichment.py:19]
    │   ├── OpenWeatherMapClient(api_key) [services/websocket-ingestion/src/weather_client.py:62]
    │   └── WeatherCache(max_size=1000, default_ttl=300) [services/websocket-ingestion/src/weather_cache.py]
    ├── weather_enrichment.start() [services/websocket-ingestion/src/weather_enrichment.py:45]
    │   ├── weather_client.start() [services/websocket-ingestion/src/weather_client.py:85]
    │   │   └── aiohttp.ClientSession(timeout=30) [services/websocket-ingestion/src/weather_client.py:88]
    │   └── weather_cache.start() [services/websocket-ingestion/src/weather_cache.py]
    ├── ConnectionManager(home_assistant_url, home_assistant_token) [services/websocket-ingestion/src/connection_manager.py:23]
    │   ├── HomeAssistantWebSocketClient() [services/websocket-ingestion/src/websocket_client.py:22]
    │   ├── EventSubscriptionManager() [services/websocket-ingestion/src/event_subscription.py:14]
    │   ├── EventProcessor() [services/websocket-ingestion/src/event_processor.py:13]
    │   ├── EventRateMonitor() [services/websocket-ingestion/src/event_rate_monitor.py]
    │   └── ErrorHandler() [services/websocket-ingestion/src/error_handler.py]
    ├── connection_manager.start() [services/websocket-ingestion/src/connection_manager.py:59]
    │   └── _connect() [services/websocket-ingestion/src/connection_manager.py:128]
    │       └── client.connect() [services/websocket-ingestion/src/websocket_client.py:40]
    │           ├── token_validator.validate_token() [services/websocket-ingestion/src/token_validator.py]
    │           ├── aiohttp.ClientSession() [services/websocket-ingestion/src/websocket_client.py:63]
    │           ├── session.ws_connect(ws_url, headers) [services/websocket-ingestion/src/websocket_client.py:69]
    │           └── _handle_authentication() [services/websocket-ingestion/src/websocket_client.py:84]
    └── asyncio.Future() [services/websocket-ingestion/src/main.py:529] # Keep running
```

### 2. WebSocket Connection and Authentication

```
HomeAssistantWebSocketClient.connect() [services/websocket-ingestion/src/websocket_client.py:40]
├── TokenValidator.validate_token() [services/websocket-ingestion/src/token_validator.py]
│   └── HTTP GET request to Home Assistant /api/ [services/websocket-ingestion/src/token_validator.py]
├── aiohttp.ClientSession() [services/websocket-ingestion/src/websocket_client.py:63]
├── session.ws_connect() [services/websocket-ingestion/src/websocket_client.py:69]
│   ├── WebSocket URL: {base_url}/api/websocket
│   ├── Headers: Authorization: Bearer {token}, User-Agent: HA-Ingestor/1.0
│   └── WebSocket connection established
└── _handle_authentication() [services/websocket-ingestion/src/websocket_client.py:84]
    ├── Receive auth_required message from Home Assistant
    ├── Send auth message with token
    ├── Receive auth_ok message from Home Assistant
    └── Set is_authenticated = True
```

### 3. Event Subscription Setup

```
ConnectionManager._on_connect() [services/websocket-ingestion/src/connection_manager.py:278]
├── EventSubscriptionManager.subscribe_to_events() [services/websocket-ingestion/src/event_subscription.py]
│   └── client.send_message() [services/websocket-ingestion/src/websocket_client.py:181]
│       ├── json.dumps(message) [services/websocket-ingestion/src/websocket_client.py:196]
│       └── websocket.send_str() [services/websocket-ingestion/src/websocket_client.py:196]
└── client.listen() [services/websocket-ingestion/src/websocket_client.py:203]
    └── asyncio.create_task(_listen_loop()) [services/websocket-ingestion/src/websocket_client.py]
        └── async for msg in websocket [services/websocket-ingestion/src/websocket_client.py:210]
            ├── json.loads(msg.data) [services/websocket-ingestion/src/websocket_client.py:213]
            └── on_message(data) [services/websocket-ingestion/src/websocket_client.py:217]
```

### 4. Event Reception and Initial Processing

```
HomeAssistantWebSocketClient.listen() [services/websocket-ingestion/src/websocket_client.py:203]
└── async for msg in websocket [services/websocket-ingestion/src/websocket_client.py:210]
    ├── json.loads(msg.data) [services/websocket-ingestion/src/websocket_client.py:213]
    └── on_message(data) [services/websocket-ingestion/src/websocket_client.py:217]
        └── ConnectionManager._on_message() [services/websocket-ingestion/src/connection_manager.py:298]
            ├── event_subscription.handle_subscription_result() [services/websocket-ingestion/src/event_subscription.py:110]
            ├── event_subscription.handle_event_message() [services/websocket-ingestion/src/event_subscription.py:146]
            │   ├── Update statistics [services/websocket-ingestion/src/event_subscription.py:162-165]
            │   └── Call subscription handlers [services/websocket-ingestion/src/event_subscription.py:171-172]
            ├── event_processor.process_event() [services/websocket-ingestion/src/event_processor.py:162]
            │   ├── validate_event_data() [services/websocket-ingestion/src/event_processor.py]
            │   ├── extract_event_data() [services/websocket-ingestion/src/event_processor.py:162]
            │   │   ├── _extract_state_changed_data() [services/websocket-ingestion/src/event_processor.py:200]
            │   │   ├── _extract_service_called_data() [services/websocket-ingestion/src/event_processor.py]
            │   │   └── _extract_generic_data() [services/websocket-ingestion/src/event_processor.py:187]
            │   └── Return processed_event
            ├── event_rate_monitor.record_event() [services/websocket-ingestion/src/event_rate_monitor.py]
            └── on_event(processed_event) [services/websocket-ingestion/src/connection_manager.py:318]
                └── WebSocketIngestionService._on_event() [services/websocket-ingestion/src/main.py:261]
```

### 5. Event Enrichment and Processing

```
WebSocketIngestionService._on_event() [services/websocket-ingestion/src/main.py:261]
├── generate_correlation_id() [shared/logging_config.py]
├── log_with_context() [shared/logging_config.py]
├── weather_enrichment.enrich_event() [services/websocket-ingestion/src/weather_enrichment.py:57]
│   ├── _determine_location() [services/websocket-ingestion/src/weather_enrichment.py:113]
│   │   └── Return default_location [services/websocket-ingestion/src/weather_enrichment.py:133]
│   ├── _get_weather_data() [services/websocket-ingestion/src/weather_enrichment.py:135]
│   │   ├── weather_cache.get() [services/websocket-ingestion/src/weather_cache.py]
│   │   └── weather_client.get_current_weather() [services/websocket-ingestion/src/weather_client.py:100]
│   │       ├── _apply_rate_limit() [services/websocket-ingestion/src/weather_client.py:171]
│   │       ├── aiohttp.ClientSession.get() [services/websocket-ingestion/src/weather_client.py:126]
│   │       │   └── HTTP GET https://api.openweathermap.org/data/2.5/weather [3RD PARTY API]
│   │       │       ├── Parameters: q=location, appid=api_key, units=metric
│   │       │       └── Response: JSON weather data
│   │       ├── WeatherData(data) [services/websocket-ingestion/src/weather_client.py:15]
│   │       └── weather_cache.put() [services/websocket-ingestion/src/weather_cache.py]
│   └── Add weather data to event [services/websocket-ingestion/src/weather_enrichment.py:82-85]
├── batch_processor.add_event() [services/websocket-ingestion/src/batch_processor.py:90]
│   ├── batch_lock.acquire() [services/websocket-ingestion/src/batch_processor.py:100]
│   ├── current_batch.append() [services/websocket-ingestion/src/batch_processor.py:102]
│   └── Check if batch is full [services/websocket-ingestion/src/batch_processor.py:105]
│       └── _process_current_batch() [services/websocket-ingestion/src/batch_processor.py:106]
└── log_with_context() [shared/logging_config.py]
```

### 6. Batch Processing and Async Event Processing

```
BatchProcessor._process_current_batch() [services/websocket-ingestion/src/batch_processor.py:132]
├── Copy current_batch [services/websocket-ingestion/src/batch_processor.py:137]
├── Clear current_batch [services/websocket-ingestion/src/batch_processor.py:138]
├── _process_batch() [services/websocket-ingestion/src/batch_processor.py:164]
│   └── Call registered batch handlers [services/websocket-ingestion/src/batch_processor.py:177]
│       └── WebSocketIngestionService._process_batch() [services/websocket-ingestion/src/main.py:310]
│           ├── async_event_processor.process_event() [services/websocket-ingestion/src/async_event_processor.py:83]
│           │   └── event_queue.put() [services/websocket-ingestion/src/event_queue.py:59]
│           │       ├── Create queue_item with metadata [services/websocket-ingestion/src/event_queue.py:73-78]
│           │       └── queue.put_nowait() [services/websocket-ingestion/src/event_queue.py:82]
│           └── http_client.send_event() [services/websocket-ingestion/src/http_client.py:21]
│               ├── session.post() [services/websocket-ingestion/src/http_client.py:27]
│               │   └── HTTP POST {enrichment_url}/events [INTERNAL API CALL]
│               │       ├── URL: http://enrichment-pipeline:8002/events
│               │       ├── Headers: Content-Type: application/json
│               │       ├── Body: JSON event data
│               │       └── Response: HTTP 200 OK
│               └── Retry logic with exponential backoff [services/websocket-ingestion/src/http_client.py:25-42]
└── Update statistics [services/websocket-ingestion/src/batch_processor.py:149-162]
```

### 7. Async Event Processing Workers

```
AsyncEventProcessor._worker() [services/websocket-ingestion/src/async_event_processor.py:110]
└── while is_running [services/websocket-ingestion/src/async_event_processor.py:114]
    ├── event_queue.get() [services/websocket-ingestion/src/event_queue.py:103]
    │   └── asyncio.wait_for(timeout=1.0) [services/websocket-ingestion/src/async_event_processor.py:117-120]
    ├── _process_single_event() [services/websocket-ingestion/src/async_event_processor.py:145]
    │   └── Call registered event handlers [services/websocket-ingestion/src/async_event_processor.py:149-153]
    │       └── InfluxDBBatchWriter.write_event() [services/websocket-ingestion/src/influxdb_batch_writer.py:107]
    │           ├── schema.create_event_point() [services/websocket-ingestion/src/influxdb_schema.py:56]
    │           │   ├── Point(MEASUREMENT_EVENTS) [services/websocket-ingestion/src/influxdb_schema.py:94]
    │           │   ├── _add_event_tags() [services/websocket-ingestion/src/influxdb_schema.py:98]
    │           │   └── _add_event_fields() [services/websocket-ingestion/src/influxdb_schema.py:101]
    │           ├── batch_lock.acquire() [services/websocket-ingestion/src/influxdb_batch_writer.py:125]
    │           ├── current_batch.append() [services/websocket-ingestion/src/influxdb_batch_writer.py:126]
    │           └── Check if batch is full [services/websocket-ingestion/src/influxdb_batch_writer.py:129]
    │               └── _process_current_batch() [services/websocket-ingestion/src/influxdb_batch_writer.py:130]
    ├── Record processing time [services/websocket-ingestion/src/async_event_processor.py:125-128]
    └── event_queue.task_done() [services/websocket-ingestion/src/async_event_processor.py:131]
```

### 8. InfluxDB Storage Operations

```
InfluxDBBatchWriter._process_current_batch() [services/websocket-ingestion/src/influxdb_batch_writer.py]
├── Copy current_batch [services/websocket-ingestion/src/influxdb_batch_writer.py]
├── Clear current_batch [services/websocket-ingestion/src/influxdb_batch_writer.py]
├── influxdb_connection.write_points() [services/websocket-ingestion/src/influxdb_wrapper.py:230]
│   ├── InfluxDBClient.write_api.write() [services/websocket-ingestion/src/influxdb_wrapper.py:246-251]
│   │   ├── asyncio.to_thread() [services/websocket-ingestion/src/influxdb_wrapper.py:246]
│   │   ├── write_api.write(bucket, org, record=points) [InfluxDB Client]
│   │   └── InfluxDB HTTP API call [DATABASE STORAGE]
│   │       ├── URL: {influxdb_url}/api/v2/write
│   │       ├── Headers: Authorization: Token {token}, Content-Type: text/plain
│   │       ├── Parameters: org={org}, bucket={bucket}, precision=ms
│   │       ├── Body: Line protocol formatted data
│   │       └── Response: HTTP 204 No Content
│   └── Log success/failure [services/websocket-ingestion/src/influxdb_wrapper.py:253-259]
└── Update statistics [services/websocket-ingestion/src/influxdb_batch_writer.py]
```

### 9. Enrichment Pipeline Service Processing

```
EnrichmentPipelineService.process_event() [services/enrichment-pipeline/src/main.py:159]
├── generate_correlation_id() [shared/logging_config.py]
├── data_validator.validate_event() [services/enrichment-pipeline/src/data_validator.py]
│   ├── Validate event structure [services/enrichment-pipeline/src/data_validator.py]
│   ├── Validate required fields [services/enrichment-pipeline/src/data_validator.py]
│   └── Return validation_results
├── data_normalizer.normalize_event() [services/enrichment-pipeline/src/data_normalizer.py:55]
│   ├── _normalize_timestamps() [services/enrichment-pipeline/src/data_normalizer.py:107]
│   ├── _normalize_state_values() [services/enrichment-pipeline/src/data_normalizer.py]
│   ├── _normalize_units() [services/enrichment-pipeline/src/data_normalizer.py]
│   ├── _extract_entity_metadata() [services/enrichment-pipeline/src/data_normalizer.py]
│   └── _validate_normalized_data() [services/enrichment-pipeline/src/data_normalizer.py:89]
├── influxdb_client.write_event() [services/enrichment-pipeline/src/influxdb_wrapper.py]
│   ├── Create InfluxDB Point [services/enrichment-pipeline/src/influxdb_wrapper.py]
│   ├── InfluxDBClient.write_api.write() [InfluxDB Client]
│   └── InfluxDB HTTP API call [DATABASE STORAGE]
│       ├── URL: {influxdb_url}/api/v2/write
│       ├── Headers: Authorization: Token {token}
│       ├── Parameters: org={org}, bucket={bucket}
│       └── Body: Line protocol data
├── quality_metrics.record_processing_result() [services/enrichment-pipeline/src/quality_metrics.py]
└── quality_alerts.check_quality_thresholds() [services/enrichment-pipeline/src/quality_alerts.py]
```

## 3rd Party API Calls

### OpenWeatherMap API
- **URL**: `https://api.openweathermap.org/data/2.5/weather`
- **Method**: GET
- **Parameters**: 
  - `q`: Location (e.g., "London,UK")
  - `appid`: API key
  - `units`: "metric"
- **Rate Limiting**: 1 second delay between requests
- **Caching**: 5-minute TTL in WeatherCache
- **Fallback**: Uses cached data if API fails

### Home Assistant API
- **WebSocket URL**: `{base_url}/api/websocket`
- **Authentication**: Bearer token in Authorization header
- **Token Validation**: HTTP GET to `/api/` endpoint
- **Event Subscription**: WebSocket message with event type filters

## Database Storage Operations

### InfluxDB Operations
- **Primary Storage**: Time-series data in InfluxDB
- **Write Operations**: 
  - Batch writes via InfluxDB HTTP API
  - Line protocol format
  - Asynchronous writes with retry logic
- **Schema**: 
  - Measurement: `home_assistant_events`
  - Tags: entity_id, domain, device_class, area, location, weather_condition, event_type
  - Fields: state, old_state, attributes, temperature, humidity, pressure, etc.
- **Retention Policies**: 
  - Raw data: 1 year
  - Daily summaries: 5 years

### Data Persistence
- **Event Queue**: In-memory with optional disk persistence
- **Weather Cache**: In-memory LRU cache with TTL
- **Batch Processing**: Memory-based batching with configurable size/timeout

## Error Handling and Resilience

### Connection Management
- **WebSocket Reconnection**: Exponential backoff with jitter
- **InfluxDB Reconnection**: Health checks every 60 seconds
- **HTTP Client Retry**: 3 attempts with exponential backoff

### Error Recovery
- **Queue Overflow**: Disk persistence for overflow events
- **API Failures**: Fallback to cached data
- **Processing Failures**: Retry with backoff, dead letter queue

## Performance Characteristics

### Throughput
- **Batch Size**: Configurable (default 100 events)
- **Batch Timeout**: Configurable (default 5 seconds)
- **Worker Count**: Configurable (default 10 workers)
- **Rate Limiting**: Configurable processing rate limit

### Memory Management
- **Event Queue**: Bounded queue (default 10,000 events)
- **Weather Cache**: LRU cache (default 1,000 entries)
- **Batch Processing**: Memory-efficient batching
- **Memory Monitoring**: Configurable memory limits

## Monitoring and Observability

### Logging
- **Structured Logging**: JSON format with correlation IDs
- **Performance Monitoring**: Processing time tracking
- **Error Tracking**: Comprehensive error logging with context

### Metrics
- **Event Processing**: Success/failure rates, processing times
- **API Calls**: Success rates, response times, error counts
- **Database Operations**: Write success rates, batch sizes
- **System Health**: Memory usage, queue depths, connection status

## Configuration

### Environment Variables
- `HOME_ASSISTANT_URL`: Home Assistant instance URL
- `HOME_ASSISTANT_TOKEN`: Authentication token
- `WEATHER_API_KEY`: OpenWeatherMap API key
- `INFLUXDB_URL`: InfluxDB server URL
- `INFLUXDB_TOKEN`: InfluxDB authentication token
- `INFLUXDB_ORG`: InfluxDB organization
- `INFLUXDB_BUCKET`: InfluxDB bucket name
- `MAX_WORKERS`: Number of async workers
- `BATCH_SIZE`: Events per batch
- `BATCH_TIMEOUT`: Batch timeout in seconds

This call tree represents the complete event lifecycle from WebSocket connection to final storage, including all function calls, storage operations, and 3rd party API integrations.
