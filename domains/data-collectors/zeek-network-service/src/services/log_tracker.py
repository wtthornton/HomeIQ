"""Log file position tracker for Zeek JSON logs.

Tracks seek offsets per log file to avoid re-processing on restart.
Handles Zeek's 5-minute log rotation by detecting inode changes and
file-size resets.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from homeiq_observability.logging_config import setup_logging

logger = setup_logging("zeek-log-tracker")


class LogTracker:
    """Tracks read positions in Zeek log files across restarts.

    Persists offsets to a JSON state file on a persistent volume so the
    service can resume from its last position after a container restart.
    """

    def __init__(self, log_dir: str, state_dir: str) -> None:
        self.log_dir = Path(log_dir)
        self.state_dir = Path(state_dir)
        self.state_file = self.state_dir / "offsets.json"
        self._offsets: dict[str, dict] = {}

    def load_offsets(self) -> None:
        """Load saved offsets from the state file."""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text())
                self._offsets = data
                logger.info(
                    "Loaded offsets for %d log files from %s",
                    len(self._offsets),
                    self.state_file,
                )
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to load offsets, starting fresh: %s", e)
                self._offsets = {}
        else:
            logger.info("No saved offsets found, starting fresh")

    def save_offsets(self) -> None:
        """Persist current offsets to the state file."""
        try:
            self.state_file.write_text(json.dumps(self._offsets, indent=2))
        except OSError as e:
            logger.error("Failed to save offsets: %s", e)

    def get_current_log_path(self, log_name: str) -> Path | None:
        """Get the path to the current (non-rotated) log file.

        Zeek names current logs as e.g. ``conn.log`` and rotated logs as
        ``conn.2026-03-16-14-30-00.log``. We always read the current file.
        """
        path = self.log_dir / log_name
        return path if path.exists() else None

    def read_new_lines(self, log_name: str) -> list[str]:
        """Read new lines from a Zeek log file since last read.

        Detects log rotation by comparing the file's inode and size against
        the saved state. If rotation is detected, the offset resets to 0.

        Returns:
            List of new JSON lines (stripped, non-empty).
        """
        path = self.get_current_log_path(log_name)
        if not path:
            return []

        try:
            stat = path.stat()
        except OSError:
            return []

        current_inode = stat.st_ino
        current_size = stat.st_size

        saved = self._offsets.get(log_name, {})
        saved_offset = saved.get("offset", 0)
        saved_inode = saved.get("inode", 0)

        # Detect rotation: inode changed or file shrank
        if current_inode != saved_inode or current_size < saved_offset:
            logger.info(
                "Log rotation detected for %s (inode %s→%s, size %s→%s), resetting offset",
                log_name,
                saved_inode,
                current_inode,
                saved_offset,
                current_size,
            )
            saved_offset = 0

        if current_size <= saved_offset:
            return []

        lines: list[str] = []
        try:
            with open(path, encoding="utf-8") as f:
                f.seek(saved_offset)
                for line in f:
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#"):
                        lines.append(stripped)
                new_offset = f.tell()
        except OSError as e:
            logger.error("Error reading %s: %s", log_name, e)
            return []

        self._offsets[log_name] = {
            "offset": new_offset,
            "inode": current_inode,
            "last_read": time.time(),
        }

        return lines

    def get_log_freshness(self) -> float | None:
        """Seconds since any log file was last modified, or None if no logs exist."""
        now = time.time()
        newest_mtime: float | None = None

        for log_name in [
            "conn.log", "dns.log", "dhcp.log", "dhcpfp.log",
            "ssl.log", "ja3.log", "ja4.log", "hassh.log", "software.log",
            "mqtt_connect.log", "mqtt_publish.log", "mqtt_subscribe.log",
            "x509.log",
        ]:
            path = self.log_dir / log_name
            if path.exists():
                try:
                    mtime = path.stat().st_mtime
                    if newest_mtime is None or mtime > newest_mtime:
                        newest_mtime = mtime
                except OSError:
                    continue

        if newest_mtime is None:
            return None

        return now - newest_mtime
