"""The status-change contract for a hygiene issue.

Kept out of test_hygiene_router.py because that module's autouse fixture needs
a live Postgres; these assert the request model alone.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from src.api.hygiene_router import StatusUpdateRequest


class TestIgnoringRequiresAReason:
    """Dismissing a finding must state why.

    An `ignored` row with no readable reason is indistinguishable from
    suppressing the finding: the open count drops and the judgement behind it
    is gone. A reviewer checks the reason, not the number.
    """

    def test_ignored_without_a_reason_is_rejected(self):
        with pytest.raises(ValidationError, match="reason is required"):
            StatusUpdateRequest(status="ignored")

    def test_ignored_with_a_blank_reason_is_rejected(self):
        with pytest.raises(ValidationError, match="reason is required"):
            StatusUpdateRequest(status="ignored", reason="   ")

    def test_ignored_with_a_reason_is_accepted(self):
        payload = StatusUpdateRequest(
            status="ignored",
            reason="HA ships add-on CPU/memory diagnostics disabled by default",
        )
        assert payload.reason.startswith("HA ships")

    def test_resolved_and_open_need_no_reason(self):
        assert StatusUpdateRequest(status="resolved").reason is None
        assert StatusUpdateRequest(status="open").reason is None

    def test_an_unknown_status_is_still_rejected(self):
        with pytest.raises(ValidationError):
            StatusUpdateRequest(status="dismissed", reason="because")
