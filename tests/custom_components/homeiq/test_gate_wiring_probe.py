"""Deliberate failure proving the CI gate is wired (TAP-6168 acceptance).

This file exists only on the first commit of the PR; the follow-up commit
removes it after the job is observed red.
"""


def test_deliberate_failure_proves_gate_is_wired() -> None:
    raise AssertionError("TAP-6168 wiring probe: this run must be red")
