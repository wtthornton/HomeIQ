# InfluxDB Python Client Patterns
**Context7 KB Cache**

**Library:** InfluxDB Python Client (/influxcommunity/influxdb3-python)  
**Topic:** Write, query, continuous aggregates, retention  
**Retrieved:** October 10, 2025  
**Code Snippets:** 27 available  
**Trust Score:** 7.7

---

## Writing Data to InfluxDB

### Using Point Class (Recommended)

```python
from influxdb_client_3 import Point

point = Point("measurement_name") \
    .tag("location", "london") \
    .tag("sensor_type", "temperature") \
    .field("temperature", 42.0) \
    .field("humidity", 65.0) \
    .time(datetime.now())

client.write(point)
```

### Using Line Protocol (Alternative)

```python
line_protocol = "measurement fieldname=0"
client.write(line_protocol)
```

### Batch Writing with Error Handling

```python
from influxdb_client_3 import write_client_options, WriteOptions, InfluxDBError

class BatchingCallback:
    """Handle batch write callbacks"""
    
    def __init__(self):
        self.write_count = 0
    
    def success(self, conf, data: str):
        self.write_count += 1
        print(f"Written batch: {conf}")
    
    def error(self, conf, data: str, exception: InfluxDBError):
        print(f"Cannot write batch: {conf}, data: {data} due: {exception}")
    
    def retry(self, conf, data: str, exception: InfluxDBError):
        print(f"Retryable error for batch: {conf}, retry: {exception}")

callback = BatchingCallback()

write_options = WriteOptions(
    batch_size=100,
    flush_interval=10_000,  # 10 seconds
    jitter_interval=2_000,
    retry_interval=5_000,
    max_retries=5,
    max_retry_delay=30_000,
    exponential_base=2
)

wco = write_client_options(
    success_callback=callback.success,
    error_callback=callback.error,
    retry_callback=callback.retry,
    write_options=write_options
)

client = InfluxDBClient3(
    token="TOKEN",
    host="influxdb:8086",
    database="home_assistant",
    write_client_options=wco
)
```

---

## Querying Data

### Query with SQL

```python
query = '''
SELECT * FROM measurement 
WHERE time > now() - 1h 
ORDER BY time
'''

table = client.query(query=query, language='sql', mode='all')
print(table)
```

### Query with InfluxQL

```python
query = '''
SELECT count("name") 
FROM measurement 
WHERE time > now() - 1h 
GROUP BY time(10m), tag_name
'''

table = client.query(query=query, language='influxql', mode='all')
```

### Query Modes

```python
# Return as Arrow table
table = client.query(query=query, mode='all')

# Return as Pandas DataFrame
df = client.query(query=query, mode='pandas')

# Return as Polars DataFrame
df = client.query(query=query, mode='polars')
```

---

## Working with Query Results

### Save Results to Parquet

```python
import pyarrow.parquet as pq

# Query returns Arrow table
table = client.query(query=query, language='sql', mode='all')

# Write to Parquet file
pq.write_table(table, 'data.parquet', compression='gzip')
```

### Process with PyArrow

```python
# Query as Arrow table
table = client.query(query=query, mode='all')

# Aggregate with PyArrow
aggregation = table.group_by(["tag1", "tag2"]).aggregate([
    ("field_name", "count"),
    ("field_name", "mean")
])

df = aggregation.to_pandas()
```

---

## Writing DataFrames

### Write Pandas DataFrame

```python
import pandas as pd

df = pd.DataFrame({
    'timestamp': [...],
    'entity_id': [...],
    'value': [...]
})

client._write_api.write(
    bucket="events",
    record=df,
    data_frame_measurement_name='home_assistant_events',
    data_frame_tag_columns=['entity_id', 'domain'],
    data_frame_timestamp_column='timestamp'
)
```

### Write from CSV File

```python
client.write_file(
    file='./data.csv',
    timestamp_column='time',
    tag_columns=["provider", "deviceID"],
    measurement_name='measurements'
)
```

---

## Patterns for HA Ingestor

### Standard Write Pattern

```python
from influxdb_client_3 import InfluxDBClient3, Point
import os

class InfluxDBWriter:
    """Standard InfluxDB writer for HA Ingestor services"""
    
    def __init__(self):
        self.client = InfluxDBClient3(
            host=os.getenv('INFLUXDB_URL', 'http://influxdb:8086'),
            token=os.getenv('INFLUXDB_TOKEN'),
            database=os.getenv('INFLUXDB_BUCKET', 'events'),
            org=os.getenv('INFLUXDB_ORG', 'home_assistant')
        )
    
    async def write_carbon_intensity(self, data: dict):
        """Write carbon intensity data"""
        
        point = Point("carbon_intensity") \
            .tag("region", data['region']) \
            .tag("grid_operator", data['grid_operator']) \
            .field("carbon_intensity_gco2_kwh", data['carbon_intensity']) \
            .field("renewable_percentage", data['renewable_percentage']) \
            .field("forecast_1h", data['forecast_1h']) \
            .time(data['timestamp'])
        
        self.client.write(point)
    
    async def write_electricity_pricing(self, data: dict):
        """Write electricity pricing data"""
        
        point = Point("electricity_pricing") \
            .tag("provider", data['provider']) \
            .tag("currency", data['currency']) \
            .field("current_price", data['current_price']) \
            .field("peak_period", data['peak_period']) \
            .time(data['timestamp'])
        
        self.client.write(point)
```

### Query Pattern for Materialized Views

```python
async def query_daily_energy(entity_id: str, days: int = 30):
    """Query materialized view (fast)"""
    
    query = f'''
    SELECT * FROM mv_daily_energy_by_device
    WHERE entity_id = '{entity_id}'
    AND time > now() - {days}d
    ORDER BY time
    '''
    
    result = client.query(query=query, language='sql', mode='pandas')
    return result
```

---

**Source:** Context7 via /influxcommunity/influxdb3-python  
**Usage:** InfluxDB operations in all data source services  
**Cached:** 2025-10-10

