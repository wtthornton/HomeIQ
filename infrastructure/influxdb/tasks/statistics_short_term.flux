// 5-minute downsample of raw Home Assistant events.
//
// data-api routes /api/v1/events by window (events_endpoints.py:945): <=10 days
// reads the raw `home_assistant_events` measurement, 10-30 days reads
// `statistics_short_term`, and beyond 30 days reads `statistics`. Nothing wrote
// either statistics measurement, so every query wider than 10 days returned an
// empty list with HTTP 200. This task and its hourly sibling populate them.
//
// Two fields are emitted per window, because HA states are not all numeric:
//
//   count - how many state changes each entity recorded. Defined for every
//           entity, including `on`/`off`/`unknown` ones, so "which entities were
//           active" survives downsampling. This is what the events endpoint reads.
//   mean  - the arithmetic mean, emitted only for entities whose states parse as
//           numbers. Meaningless for a light, so it is simply absent there
//           rather than faked.
//
// Both are computed from raw rather than the hourly tier from this one, so the
// hourly mean is a true mean and not an unweighted mean of means.

option task = {name: "homeiq_statistics_short_term", every: 5m, offset: 1m}

raw =
    from(bucket: "home_assistant_events")
        |> range(start: -task.every)
        |> filter(fn: (r) => r._measurement == "home_assistant_events")
        |> filter(fn: (r) => r._field == "state_value")

// Every entity, numeric or not.
raw
    |> aggregateWindow(every: 5m, fn: count, createEmpty: false)
    |> set(key: "_measurement", value: "statistics_short_term")
    |> set(key: "_field", value: "count")
    |> to(bucket: "home_assistant_events")

// Numeric entities only. The regex is the guard: float() on "on" fails the whole
// task, so non-numeric states are dropped before the cast, never after.
raw
    |> filter(fn: (r) => r._value =~ /^-?[0-9]+(\.[0-9]+)?$/)
    |> map(fn: (r) => ({r with _value: float(v: r._value)}))
    |> aggregateWindow(every: 5m, fn: mean, createEmpty: false)
    |> set(key: "_measurement", value: "statistics_short_term")
    |> set(key: "_field", value: "mean")
    |> to(bucket: "home_assistant_events")
