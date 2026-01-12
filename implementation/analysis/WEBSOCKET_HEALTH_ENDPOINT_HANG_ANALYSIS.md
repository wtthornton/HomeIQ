# WebSocket Ingestion Health Endpoint Hang Analysis

## Problem
The `/health` endpoint at `http://localhost:8001/health` hangs/timeouts and does not return a response.

## Hypotheses

### Hypothesis A: `is_running` property blocking on state machine lock
The `is_running` property in ConnectionManager accesses `state_machine.get_state()`, which might be blocking if the state machine has a lock that's held by another operation (reconnection loop, connection attempt, etc.).

### Hypothesis B: Direct attribute access on event_subscription causing blocking
Lines 235-244 access `event_subscription.is_subscribed`, `event_subscription.total_events_received`, and `event_subscription.subscription_start_time` directly. These attributes might be accessed while being modified by the event processing loop, causing blocking or deadlock.

### Hypothesis C: `get_subscription_status()` method blocking
The `get_subscription_status()` method iterates over `self.subscriptions` dict and accesses nested structures. If subscriptions are being modified concurrently (during subscription/unsubscription), this could block.

### Hypothesis D: Historical counter database query blocking
The `historical_counter.get_total_events_received()` call might be making a blocking database query that's hanging due to database connection issues or locks.

### Hypothesis E: Exception being swallowed causing infinite wait
An exception in the health check logic might be caught but not properly handled, causing the async function to hang instead of returning an error response.

## Instrumentation Plan

Adding debug logs at key points:
1. Entry to health endpoint handler
2. Before/after connection_manager attribute access
3. Before/after get_subscription_status() call
4. Before/after historical_counter access
5. Before/after is_running property access
6. Exception handler entry points
