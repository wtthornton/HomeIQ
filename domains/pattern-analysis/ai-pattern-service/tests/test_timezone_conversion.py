"""
TAP-7307: pattern detectors derived hour/day-of-week/date features straight
off tz-aware UTC timestamps (``.dt.hour`` etc.), so a device used every
evening in Home Assistant's local timezone was recorded at the wrong hour.
Container ``TZ`` cannot fix this — the event series is already tz-aware UTC
and pandas datetime accessors report the series' own tzinfo, not the OS
timezone. The fix converts via ``tz_convert`` before deriving any feature.

This test feeds five 03:00Z events (a date range entirely inside PDT, so the
UTC offset is constant at -7h) and asserts the detected time-of-day pattern
lands on local hour 20, not UTC hour 3.
"""

import pandas as pd
import pytest
from src.pattern_analyzer.time_of_day import TimeOfDayPatternDetector


@pytest.mark.unit
def test_time_of_day_hour_is_local_not_utc():
    events = pd.DataFrame(
        {
            "device_id": ["light.living_room"] * 5,
            "timestamp": pd.to_datetime(
                [
                    "2026-07-01T03:00:00Z",
                    "2026-07-02T03:00:00Z",
                    "2026-07-03T03:00:00Z",
                    "2026-07-04T03:00:00Z",
                    "2026-07-05T03:00:00Z",
                ]
            ),
            "state": ["on"] * 5,
        }
    )

    try:
        detector = TimeOfDayPatternDetector(time_zone="America/Los_Angeles")
    except TypeError:
        # Base tree has no time_zone param at all — falls through to the
        # detector's UTC default, which is the defect this test targets.
        detector = TimeOfDayPatternDetector()
    patterns = detector.detect_patterns(events)

    assert len(patterns) == 1
    # 03:00 UTC on a PDT (UTC-7) date is 20:00 local the previous day —
    # NOT 03:00, which is what a bare `.dt.hour` on the raw UTC series
    # would have produced.
    assert patterns[0]["hour"] == 20
