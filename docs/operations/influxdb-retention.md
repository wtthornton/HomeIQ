# InfluxDB buckets & retention — declared vs. actual

**Status:** reference · **Verified live:** 2026-08-13 (TAP-6007) · **Org:** `homeiq`

## TL;DR

Every collector writes into the single **`home_assistant_events`** bucket
(365-day retention). The per-type buckets that the schema declares
(`sports_data`, `weather_data`, `system_metrics`) **exist but are empty** —
their declared retentions are not in effect anywhere. Data is separated by
**measurement name inside `home_assistant_events`**, not by bucket.

Don't re-derive this by querying; it's here so you don't have to.

## Live buckets (2026-08-13)

| Bucket | Retention | Actually holds data? |
|---|---|---|
| `home_assistant_events` | **365d** (`infinite` on the bucket object; 365d is the declared intent) | **Yes** — every measurement lands here |
| `sports_data` | infinite | **No** — 0 records, 0 measurements |
| `weather_data` | — | No |
| `system_metrics` | — | No |
| `_monitoring`, `_tasks` | 168h / 72h | InfluxDB internal |

## Where the data actually is

The `sports_data` **measurement** lives in the `home_assistant_events`
**bucket** (~12,500 points / 90d as of verification). Same pattern for the
other declared types. Verify with:

```flux
// data present here:
from(bucket: "home_assistant_events") |> range(start: -90d)
  |> filter(fn: (r) => r._measurement == "sports_data")
  |> group() |> count() |> sum()

// bucket is empty:
from(bucket: "sports_data") |> range(start: 1970-01-01T00:00:00Z)
  |> group() |> count() |> sum()
```

Run from inside the container so the token stays there:
`docker exec homeiq-influxdb influx query --token "$DOCKER_INFLUXDB_INIT_ADMIN_TOKEN" -o "$DOCKER_INFLUXDB_INIT_ORG" "<flux>"`
(reading the raw table output — parsing the annotated CSV by column index is
error-prone and gave a false "empty" the first time).

## Why (the code)

- `domains/core-platform/websocket-ingestion/src/influxdb_schema.py:49-99`
  **declares** four buckets with per-type retentions (`RETENTION_SPORTS_DATA
  = "90d"`, etc.).
- Each collector overrides that: e.g.
  `domains/data-collectors/sports-api/src/config.py:18` and
  `main.py:160,252` default `INFLUXDB_BUCKET` to `home_assistant_events` and
  write there.

So the declared 90d/180d/30d retentions govern nothing. Changing a
`RETENTION_*` constant, or setting a per-type bucket's retention, has **no
effect** until a collector is pointed at that bucket.

## Consequences / decisions this pre-answers

- **"Does sports data delete after 90d?"** No — it's in
  `home_assistant_events` (365d), kept ~4× longer than the declaration.
- **"Set the `sports_data` bucket to 90d?"** A no-op — the bucket is empty.
- To actually enforce a per-type retention, either point the collector at the
  matching bucket (then its retention applies), or delete the unused bucket +
  declaration and accept the 365d policy. This is an open design decision, not
  a bug fixed by touching retention values alone.
