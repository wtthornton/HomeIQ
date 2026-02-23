### Write Time-Series Data with Point Object in Python

Shows how to write time-series data to InfluxDB using the `Point` object. This method allows specifying measurement, tags, fields, and timestamps with precise control. It includes error handling for the write operation and ensures the client connection is closed.

```python
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime, timezone

with InfluxDBClient(url="http://localhost:8086", token="my-token", org="my-org") as client:
    write_api = client.write_api(write_options=SYNCHRONOUS)

    # Create and write a point
    point = Point("my_measurement") \
        .tag("location", "Prague") \
        .tag("sensor_id", "TLM01") \
        .field("temperature", 25.3) \
        .field("humidity", 65.0) \
        .time(datetime.now(tz=timezone.utc), WritePrecision.NS)

    try:
        write_api.write(bucket="my-bucket", org="my-org", record=point)
        print("Data written successfully")
    except Exception as e:
        print(f"Write failed: {e}")
    finally:
        client.close()
```

### Batch Write API Configuration with Callbacks

Configures batching for high-throughput writes with automatic retry and backoff strategies. It utilizes callback functions to handle success, error, and retry events during the write process. Dependencies include the influxdb-client library.

```python
from influxdb_client import InfluxDBClient, Point, WriteOptions
from influxdb_client.client.exceptions import InfluxDBError

class BatchingCallback:
    def success(self, conf, data):
        print(f"Written batch: {conf}")

    def error(self, conf, data, exception: InfluxDBError):
        print(f"Cannot write batch: {conf} due: {exception}")

    def retry(self, conf, data, exception: InfluxDBError):
        print(f"Retrying batch: {conf} due: {exception}")

with InfluxDBClient(url="http://localhost:8086", token="my-token", org="my-org") as client:
    callback = BatchingCallback()

    write_options = WriteOptions(
        batch_size=500,
        flush_interval=10_000,
        jitter_interval=2_000,
        retry_interval=5_000,
        max_retries=5,
        max_retry_delay=30_000,
        exponential_base=2
    )

    with client.write_api(
        write_options=write_options,
        success_callback=callback.success,
        error_callback=callback.error,
        retry_callback=callback.retry
    ) as write_api:
        for i in range(10000):
            point = Point("sensor_data") \
                .tag("device_id", f"sensor_{i % 100}") \
                .field("value", i * 1.5)
            write_api.write("my-bucket", "my-org", point)
```

### WriteApi

API for writing data points to InfluxDB.

```APIDOC
## WriteApi

### Description
The WriteApi provides methods to write time-series data points into InfluxDB. It supports batching and various data formats.

### Method
N/A (Class)

### Endpoint
N/A (Class)

### Parameters
N/A (Class)

### Request Example
```python
from influxdb_client.client.write_api import SYNCHRONOUS

write_api = client.write_api(write_options=SYNCHRONOUS)

# Example of writing a single point
write_api.write(bucket="my-bucket", org="my-org", record="cpu,host=server1 value=10i")

# Example of writing multiple points
points = [
    "cpu,host=server2 value=20i",
    "cpu,host=server3 value=30i"
]
write_api.write(bucket="my-bucket", org="my-org", records=points)
```

### Response
N/A (Class)
```

### Handle Batch Write Errors with Callbacks in Python

Illustrates how to handle errors during batch writes using custom callback functions. This is necessary because batch writes occur in a separate background thread, making direct exception handling impossible. The callbacks allow for success, error, and retry notifications.

```python
from influxdb_client import InfluxDBClient
from influxdb_client.client.exceptions import InfluxDBError


class BatchingCallback(object):

    def success(self, conf: (str, str, str), data: str):
        print(f"Written batch: {conf}, data: {data}")

    def error(self, conf: (str, str, str), data: str, exception: InfluxDBError):
        print(f"Cannot write batch: {conf}, data: {data} due: {exception}")

    def retry(self, conf: (str, str, str), data: str, exception: InfluxDBError):
        print(f"Retryable error occurs for batch: {conf}, data: {data} retry: {exception}")


with InfluxDBClient(url="http://localhost:8086", token="my-token", org="my-org") as client:
    callback = BatchingCallback()
    with client.write_api(success_callback=callback.success,
                          error_callback=callback.error,
                          retry_callback=callback.retry) as write_api:
        pass
```

### Write Structured Data with influxdb-python

Shows how to write data using the SeriesHelper class in the older influxdb-python library. This approach simplifies batching and committing data points with predefined fields and tags.

```python
from influxdb import InfluxDBClient
from influxdb import SeriesHelper

my_client = InfluxDBClient(host='127.0.0.1', port=8086, username='root', password='root', database='dbname')


class MySeriesHelper(SeriesHelper):
    class Meta:
        client = my_client
        series_name = 'events.stats.{server_name}'
        fields = ['some_stat', 'other_stat']
        tags = ['server_name']
        bulk_size = 5
        autocommit = True


MySeriesHelper(server_name='us.east-1', some_stat=159, other_stat=10)
MySeriesHelper(server_name='us.east-1', some_stat=158, other_stat=20)

MySeriesHelper.commit()
```

### Handle Batch Write Events in InfluxDB

Illustrates how to handle events that occur during batch writes to InfluxDB, such as success or failure notifications. This is useful for monitoring write operations.

```python
write_api_callbacks.py
```

### Asynchronous Data Write to InfluxDB

Shows how to use the `WriteApiAsync` to ingest data into InfluxDB. It supports various data formats including `Point` objects, dictionaries, and lists of these structures. The example writes two temperature points.

```python
import asyncio

from influxdb_client import Point
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync


async def main():
    async with InfluxDBClientAsync(url="http://localhost:8086", token="my-token", org="my-org") as client:

        write_api = client.write_api()

        _point1 = Point("async_m").tag("location", "Prague").field("temperature", 25.3)
        _point2 = Point("async_m").tag("location", "New York").field("temperature", 24.3)

        successfully = await write_api.write(bucket="my-bucket", record=[_point1, _point2])

        print(f" > successfully: {successfully}")


if __name__ == "__main__":
    asyncio.run(main())
```

### Synchronous Data Write - Python

Writes data points to InfluxDB using a synchronous client, ensuring that each write operation completes before the next is initiated. This is suitable for applications requiring immediate confirmation of data ingestion. Requires specifying connection details and a bucket.

```python
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

client = InfluxDBClient(url="http://localhost:8086", token="my-token", org="my-org")
write_api = client.write_api(write_options=SYNCHRONOUS)

_point1 = Point("my_measurement").tag("location", "Prague").field("temperature", 25.3)
_point2 = Point("my_measurement").tag("location", "New York").field("temperature", 24.3)

write_api.write(bucket="my-bucket", record=[_point1, _point2])

client.close()
```

### Write Data Using Line Protocol (Python)

Compares writing data points to InfluxDB using the Line Protocol format with both `influxdb-python` and `influxdb-client-python`. The newer client utilizes a `WriteAPI` configured for synchronous writes.

```python
from influxdb import InfluxDBClient

client = InfluxDBClient(host='127.0.0.1', port=8086, username='root', password='root', database='dbname')

client.write('h2o_feet,location=coyote_creek water_level=1.0 1', protocol='line')
```

```python
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

with InfluxDBClient(url='http://localhost:8086', token='my-token', org='my-org') as client:
    write_api = client.write_api(write_options=SYNCHRONOUS)

    write_api.write(bucket='my-bucket', record='h2o_feet,location=coyote_creek water_level=1.0 1')
```

### Configure and Write Data with InfluxDB Python Client

This snippet shows how to initialize the InfluxDB client and configure the write API with various options, including batch size, flush interval, retry logic, and maximum close wait time. It then demonstrates writing data in multiple formats: Line Protocol strings, byte arrays, dictionaries, Point objects, RxPy Observables, and Pandas DataFrames.

```python
from datetime import datetime, timedelta, timezone

import pandas as pd
import reactivex as rx
from reactivex import operators as ops

from influxdb_client import InfluxDBClient, Point, WriteOptions

with InfluxDBClient(url="http://localhost:8086", token="my-token", org="my-org") as _client:

    with _client.write_api(write_options=WriteOptions(batch_size=500,
                                                      flush_interval=10_000,
                                                      jitter_interval=2_000,
                                                      retry_interval=5_000,
                                                      max_retries=5,
                                                      max_retry_delay=30_000,
                                                      max_close_wait=300_000,
                                                      exponential_base=2)) as _write_client:

        """
        Write Line Protocol formatted as string
        """
        _write_client.write("my-bucket", "my-org", "h2o_feet,location=coyote_creek water_level=1.0 1")
        _write_client.write("my-bucket", "my-org", ["h2o_feet,location=coyote_creek water_level=2.0 2",
                                                    "h2o_feet,location=coyote_creek water_level=3.0 3"])

        """
        Write Line Protocol formatted as byte array
        """
        _write_client.write("my-bucket", "my-org", "h2o_feet,location=coyote_creek water_level=1.0 1".encode())
        _write_client.write("my-bucket", "my-org", ["h2o_feet,location=coyote_creek water_level=2.0 2".encode(),
                                                    "h2o_feet,location=coyote_creek water_level=3.0 3".encode()])

        """
        Write Dictionary-style object
        """
        _write_client.write("my-bucket", "my-org", {"measurement": "h2o_feet", "tags": {"location": "coyote_creek"},
                                                    "fields": {"water_level": 1.0}, "time": 1})
        _write_client.write("my-bucket", "my-org", [{"measurement": "h2o_feet", "tags": {"location": "coyote_creek"},
                                                     "fields": {"water_level": 2.0}, "time": 2},
                                                    {"measurement": "h2o_feet", "tags": {"location": "coyote_creek"},
                                                     "fields": {"water_level": 3.0}, "time": 3}])

        """
        Write Data Point
        """
        _write_client.write("my-bucket", "my-org",
                            Point("h2o_feet").tag("location", "coyote_creek").field("water_level", 4.0).time(4))
        _write_client.write("my-bucket", "my-org",
                            [Point("h2o_feet").tag("location", "coyote_creek").field("water_level", 5.0).time(5),
                             Point("h2o_feet").tag("location", "coyote_creek").field("water_level", 6.0).time(6)])

        """
        Write Observable stream
        """
        _data = rx \
            .range(7, 11) \
            .pipe(ops.map(lambda i: "h2o_feet,location=coyote_creek water_level={0}.0 {0}".format(i)))

        _write_client.write("my-bucket", "my-org", _data)

        """
        Write Pandas DataFrame
        """
        _now = datetime.now(tz=timezone.utc)
        _data_frame = pd.DataFrame(data=[["coyote_creek", 1.0], ["coyote_creek", 2.0]],
                                   index=[_now, _now + timedelta(hours=1)],
                                   columns=["location", "water_level"])

        _write_client.write("my-bucket", "my-org", record=_data_frame, data_frame_measurement_name='h2o_feet',
                            data_frame_tag_columns=['location'])
```