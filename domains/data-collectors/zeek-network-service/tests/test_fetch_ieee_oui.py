"""Tests for the build-time IEEE OUI dataset builder.

Both guards here exist to stop the image shipping a dataset that silently
resolves nothing: the origin check, and the per-source row floor.
"""

from __future__ import annotations

import gzip
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from fetch_ieee_oui import ALLOWED_ORIGIN, MIN_ROWS_PER_SOURCE, _fetch, build  # noqa: E402


def _csv(rows: int, prefix: str = "AABB") -> str:
    header = "Registry,Assignment,Organization Name,Organization Address\n"
    return header + "".join(f"MA-L,{prefix}{i:02X},Vendor {i},Somewhere\n" for i in range(rows))


class TestOriginGuard:
    """urlopen-style schemes are gone, but a stray SOURCES entry still must not fetch."""

    def test_rejects_a_host_outside_the_allowed_origin(self):
        with pytest.raises(ValueError, match="refusing to fetch"):
            _fetch("https://evil.example.com/oui.csv")

    def test_rejects_a_file_url(self):
        with pytest.raises(ValueError, match="refusing to fetch"):
            _fetch("file:///etc/passwd")

    def test_allowed_origin_is_ieee_over_https(self):
        assert ALLOWED_ORIGIN.startswith("https://")
        assert "ieee.org" in ALLOWED_ORIGIN


class TestBuild:
    def test_merges_all_three_registries(self, tmp_path: Path):
        with patch(
            "fetch_ieee_oui._fetch",
            side_effect=[
                _csv(MIN_ROWS_PER_SOURCE, "AA"),
                _csv(MIN_ROWS_PER_SOURCE, "BB"),
                _csv(MIN_ROWS_PER_SOURCE, "CC"),
            ],
        ):
            out = tmp_path / "ieee-oui.tsv.gz"
            count = build(out)

        assert count == MIN_ROWS_PER_SOURCE * 3
        lines = gzip.decompress(out.read_bytes()).decode().splitlines()
        assert len(lines) == count
        assert all("\t" in line for line in lines)

    def test_a_truncated_registry_fails_the_build(self, tmp_path: Path):
        """A captive portal or short transfer must not become a shipped dataset."""
        with (
            patch("fetch_ieee_oui._fetch", return_value=_csv(5)),
            pytest.raises(RuntimeError, match="refusing to build"),
        ):
            build(tmp_path / "ieee-oui.tsv.gz")

        assert not (tmp_path / "ieee-oui.tsv.gz").exists()

    def test_rows_missing_an_organization_are_skipped(self, tmp_path: Path):
        good = _csv(MIN_ROWS_PER_SOURCE)
        blank = good + "MA-L,FFFFFF,,Nowhere\n"
        with patch(
            "fetch_ieee_oui._fetch",
            side_effect=[blank, _csv(MIN_ROWS_PER_SOURCE, "BB"), _csv(MIN_ROWS_PER_SOURCE, "CC")],
        ):
            out = tmp_path / "ieee-oui.tsv.gz"
            build(out)

        assert "FFFFFF" not in gzip.decompress(out.read_bytes()).decode()
