<!--
library: influxdb
topic: write
context7_id: /influxdata/influxdb-client-python
cached_at: 2025-12-21T00:41:07.365907+00:00Z
cache_hits: 0
-->

# InfluxDB Write

## Write Time-Series Data with Point Object

```python
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime, timezone

with InfluxDBClient(url="http://localhost:8086", token="my-token", org="my-org") as client:
    write_api = client.write_api(write_options=SYNCHRONOUS)

    point = Point("my_measurement") \
        .tag("location", "Prague") \
        .tag("sensor_id", "TLM01") \
        .field("temperature", 25.3) \
        .field("humidity", 65.0) \
        .time(datetime.now(tz=timezone.utc), WritePrecision.NS)

    write_api.write(bucket="my-bucket", org="my-org", record=point)
```

## Write Time-Series Data with Line Protocol

```python
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

with InfluxDBClient(url="http://localhost:8086", token="my-token", org="my-org") as client:
    write_api = client.write_api(write_options=SYNCHRONOUS)

    line = "h2o_feet,location=coyote_creek water_level=8.12 1568020800000000000"
    write_api.write("my-bucket", "my-org", line)

    # Multiple measurements
    lines = [
        "h2o_feet,location=coyote_creek water_level=8.12 1568020800000000000",
        "h2o_feet,location=santa_monica water_level=2.064 1568020800000000000"
    ]
    write_api.write("my-bucket", "my-org", lines)
```

