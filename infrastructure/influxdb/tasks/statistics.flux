// Hourly downsample of raw Home Assistant events.
//
// The long-term tier data-api reads for windows beyond 30 days
// (events_endpoints.py:945). See statistics_short_term.flux for why both a
// `count` and a `mean` field are emitted, and why both are computed from the raw
// measurement rather than from the 5-minute tier.

option task = {name: "homeiq_statistics", every: 1h, offset: 5m}

raw =
    from(bucket: "home_assistant_events")
        |> range(start: -task.every)
        |> filter(fn: (r) => r._measurement == "home_assistant_events")
        |> filter(fn: (r) => r._field == "state_value")

raw
    |> aggregateWindow(every: 1h, fn: count, createEmpty: false)
    |> set(key: "_measurement", value: "statistics")
    |> set(key: "_field", value: "count")
    |> to(bucket: "home_assistant_events")

raw
    |> filter(fn: (r) => r._value =~ /^-?[0-9]+(\.[0-9]+)?$/)
    |> map(fn: (r) => ({r with _value: float(v: r._value)}))
    |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
    |> set(key: "_measurement", value: "statistics")
    |> set(key: "_field", value: "mean")
    |> to(bucket: "home_assistant_events")
