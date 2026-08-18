from src.budget import cap_rows, enforce_budget, payload_size


def test_under_budget_is_untouched():
    payload = {"points": [1, 2, 3], "count": 3, "truncated": False}
    assert enforce_budget(payload, 1024, "hours") is payload
    assert payload["truncated"] is False
    assert "hint" not in payload


def test_over_budget_drops_rows_and_flags():
    rows = [{"t": "2026-08-17T00:00:00Z", "state": "on", "i": i} for i in range(500)]
    payload = {"entity_id": "light.x", "points": rows, "count": 500, "truncated": False}
    limit = 4096
    enforce_budget(payload, limit, "hours")
    assert payload_size(payload) <= limit
    assert payload["truncated"] is True
    assert payload["hint"] == "hours"
    assert payload["count"] == len(payload["points"]) < 500
    assert len(payload["points"]) > 0


def test_multiple_lists_shrinks_the_largest_first():
    payload = {
        "power_anomalies": [{"entity_id": f"sensor.{i}"} for i in range(50)],
        "failure_predictions": [{"device_id": f"d{i}"} for i in range(5)],
        "counts": {"power": 50, "failure_risk": 5},
        "truncated": False,
    }
    enforce_budget(payload, 600, "limit")
    assert payload["truncated"] is True
    assert len(payload["failure_predictions"]) == 5 or len(payload["power_anomalies"]) <= 5


def test_cap_rows():
    rows, capped = cap_rows(list(range(10)), 3)
    assert rows == [0, 1, 2] and capped is True
    rows, capped = cap_rows([1], 3)
    assert rows == [1] and capped is False
