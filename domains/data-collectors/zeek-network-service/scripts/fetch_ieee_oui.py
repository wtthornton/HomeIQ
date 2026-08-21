"""Build the bundled IEEE OUI dataset used by :mod:`src.services.oui_lookup`.

Run at image build time. Downloads the three IEEE MAC-block registries and
normalizes them into one gzipped TSV of ``ASSIGNMENT<TAB>ORGANIZATION``.

Why all three registries, not just MA-L: IEEE subdivides 24-bit MA-L blocks
into 28-bit MA-M and 36-bit MA-S assignments, and the sub-assignee is a
different company from the block holder. Resolving on 24 bits alone therefore
names the wrong vendor for any device inside a subdivided block.

Why not a Python package: the bundled datasets in ``manuf`` and
``mac-vendor-lookup`` lag the registry. Measured against the 12 MAC prefixes
live on the reference network, ``manuf`` resolved 5; this dataset resolved 12,
including three Ring and five Amazon devices the stale sets missed.

The output is ~577 KB gzipped for ~53.7k assignments.
"""

from __future__ import annotations

import csv
import gzip
import io
import sys
from pathlib import Path

import httpx

#: (URL, human label). Order is irrelevant — lookup resolves longest-prefix-first.
SOURCES = (
    ("https://standards-oui.ieee.org/oui/oui.csv", "MA-L (24-bit)"),
    ("https://standards-oui.ieee.org/oui28/mam.csv", "MA-M (28-bit)"),
    ("https://standards-oui.ieee.org/oui36/oui36.csv", "MA-S (36-bit)"),
)

DEFAULT_OUT = Path(__file__).resolve().parent.parent / "data" / "ieee-oui.tsv.gz"

#: A registry that comes back far smaller than this is a captive-portal page or
#: a truncated transfer, not data. Failing the build beats shipping a dataset
#: that silently resolves nothing.
MIN_ROWS_PER_SOURCE = 1000


#: standards-oui.ieee.org answers urllib's default ``Python-urllib/3.x`` with
#: HTTP 418, so the agent string is load-bearing, not cosmetic.
USER_AGENT = "HomeIQ-zeek-network-service/1.0 (+https://github.com/wtthornton/HomeIQ)"


#: The only host this script reads from. httpx speaks http(s) only — unlike
#: urllib, which also accepts ``file://`` and custom schemes — but the explicit
#: check keeps a mistyped SOURCES entry from silently reaching another host.
ALLOWED_ORIGIN = "https://standards-oui.ieee.org"


def _fetch(url: str, timeout: int = 120) -> str:
    if not url.startswith(f"{ALLOWED_ORIGIN}/"):
        raise ValueError(f"refusing to fetch {url!r}: not under {ALLOWED_ORIGIN}")
    response = httpx.get(
        url, headers={"User-Agent": USER_AGENT}, timeout=timeout, follow_redirects=True
    )
    response.raise_for_status()
    return response.text


def build(out_path: Path = DEFAULT_OUT) -> int:
    """Write the normalized dataset. Returns the assignment count."""
    entries: dict[str, str] = {}

    for url, label in SOURCES:
        text = _fetch(url)
        rows = 0
        for record in csv.DictReader(io.StringIO(text)):
            assignment = (record.get("Assignment") or "").strip().upper()
            organization = (record.get("Organization Name") or "").strip()
            if not assignment or not organization:
                continue
            entries[assignment] = organization
            rows += 1
        if rows < MIN_ROWS_PER_SOURCE:
            raise RuntimeError(f"{label} returned only {rows} rows from {url}; refusing to build")
        print(f"  {label}: {rows} assignments", file=sys.stderr)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(f"{a}\t{o}" for a, o in sorted(entries.items())).encode("utf-8")
    out_path.write_bytes(gzip.compress(payload, 9))
    print(f"Wrote {len(entries)} assignments to {out_path}", file=sys.stderr)
    return len(entries)


if __name__ == "__main__":
    build(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT)
