"""Test fixtures for zeek-network-service."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Set test environment variables before importing app modules
os.environ.setdefault("INFLUXDB_TOKEN", "test-token")
os.environ.setdefault("SERVICE_PORT", "8048")


@pytest.fixture
def tmp_log_dir(tmp_path: Path) -> Path:
    """Create a temporary directory with sample Zeek log files."""
    return tmp_path


@pytest.fixture
def sample_conn_log_lines() -> list[str]:
    """Sample conn.log JSON entries as Zeek would produce them."""
    return [
        json.dumps({
            "ts": 1710600000.0,
            "uid": "CYnvWc3enJjQC9w5y2",
            "id.orig_h": "192.168.1.42",
            "id.orig_p": 55432,
            "id.resp_h": "93.184.216.34",
            "id.resp_p": 443,
            "proto": "tcp",
            "service": "ssl",
            "duration": 1.234,
            "orig_bytes": 1024,
            "resp_bytes": 4096,
            "conn_state": "SF",
            "orig_pkts": 10,
            "resp_pkts": 8,
            "missed_bytes": 0,
        }),
        json.dumps({
            "ts": 1710600001.0,
            "uid": "CaBk2m1PFbOSBF9fZ",
            "id.orig_h": "192.168.1.100",
            "id.orig_p": 12345,
            "id.resp_h": "192.168.1.1",
            "id.resp_p": 53,
            "proto": "udp",
            "service": "dns",
            "duration": 0.005,
            "orig_bytes": 64,
            "resp_bytes": 256,
            "conn_state": "SF",
            "orig_pkts": 1,
            "resp_pkts": 1,
            "missed_bytes": 0,
        }),
        # Docker bridge traffic (should be excluded by BPF, but test parser handles it)
        json.dumps({
            "ts": 1710600002.0,
            "uid": "Ct7jIp3IeLb63dEHe",
            "id.orig_h": "172.18.0.5",
            "id.orig_p": 8080,
            "id.resp_h": "172.18.0.10",
            "id.resp_p": 8086,
            "proto": "tcp",
            "service": "http",
            "duration": 0.01,
            "orig_bytes": 128,
            "resp_bytes": 512,
            "conn_state": "SF",
            "orig_pkts": 2,
            "resp_pkts": 2,
            "missed_bytes": 0,
        }),
    ]


@pytest.fixture
def sample_dns_log_lines() -> list[str]:
    """Sample dns.log JSON entries."""
    return [
        json.dumps({
            "ts": 1710600000.0,
            "uid": "CYnvWc3enJjQC9w5y2",
            "id.orig_h": "192.168.1.42",
            "id.orig_p": 55432,
            "id.resp_h": "192.168.1.1",
            "id.resp_p": 53,
            "proto": "udp",
            "query": "api.tuya.com",
            "qtype_name": "A",
            "rcode_name": "NOERROR",
            "rtt": 0.012,
            "answers": ["1.2.3.4", "5.6.7.8"],
            "TTLs": [300.0, 300.0],
            "rejected": False,
        }),
        json.dumps({
            "ts": 1710600001.0,
            "uid": "CaBk2m1PFbOSBF9fZ",
            "id.orig_h": "192.168.1.100",
            "id.orig_p": 12345,
            "id.resp_h": "192.168.1.1",
            "id.resp_p": 53,
            "proto": "udp",
            "query": "time.google.com",
            "qtype_name": "A",
            "rcode_name": "NOERROR",
            "rtt": 0.008,
            "answers": ["216.239.35.0"],
            "TTLs": [60.0],
            "rejected": False,
        }),
    ]


@pytest.fixture
def mock_influx_writer() -> AsyncMock:
    """Mock InfluxWriter for unit tests."""
    writer = AsyncMock()
    writer.write_success_count = 0
    writer.write_failure_count = 0
    writer.buffer_size = 0
    writer.last_write_time = None
    writer.last_write_error = None
    return writer


@pytest.fixture
def sample_dhcp_log_lines() -> list[str]:
    """Sample dhcp.log JSON entries."""
    return [
        json.dumps({
            "ts": 1710600000.0,
            "uids": ["CYnvWc3enJjQC9w5y2"],
            "client_addr": "192.168.1.42",
            "assigned_addr": "192.168.1.42",
            "mac": "24:6f:28:aa:bb:cc",
            "host_name": "esp32-livingroom",
            "lease_time": 86400.0,
            "msg_types": ["DISCOVER", "OFFER", "REQUEST", "ACK"],
        }),
        json.dumps({
            "ts": 1710600001.0,
            "uids": ["CaBk2m1PFbOSBF9fZ"],
            "client_addr": "192.168.1.100",
            "assigned_addr": "192.168.1.100",
            "mac": "B8:27:EB:11:22:33",
            "host_name": "raspberrypi",
            "lease_time": 86400.0,
            "msg_types": ["REQUEST", "ACK"],
        }),
    ]


@pytest.fixture
def sample_dhcpfp_log_lines() -> list[str]:
    """Sample dhcpfp.log (KYD) JSON entries."""
    return [
        json.dumps({
            "ts": 1710600000.0,
            "mac": "24:6f:28:aa:bb:cc",
            "client_addr": "192.168.1.42",
            "fingerprint": "1,33,3,6,15,26,28,51,58,59",
            "vendor_class": "dhcpcd-6.7.1:Linux-5.4",
        }),
    ]


@pytest.fixture
def sample_ja3_log_lines() -> list[str]:
    """Sample ja3.log JSON entries."""
    return [
        json.dumps({
            "ts": 1710600000.0,
            "uid": "CYnvWc3enJjQC9w5y2",
            "id.orig_h": "192.168.1.42",
            "id.orig_p": 55432,
            "id.resp_h": "93.184.216.34",
            "id.resp_p": 443,
            "ja3": "e7d705a3286e19ea42f587b344ee6865",
            "ja3s": "ec74a5c51106f0419184d0dd08fb05bc",
        }),
    ]


@pytest.fixture
def sample_ja4_log_lines() -> list[str]:
    """Sample ja4.log JSON entries."""
    return [
        json.dumps({
            "ts": 1710600000.0,
            "uid": "CYnvWc3enJjQC9w5y2",
            "id.orig_h": "192.168.1.42",
            "id.orig_p": 55432,
            "id.resp_h": "93.184.216.34",
            "id.resp_p": 443,
            "ja4": "t13d1516h2_8daaf6152771_b186095e22b6",
        }),
    ]


@pytest.fixture
def sample_hassh_log_lines() -> list[str]:
    """Sample hassh.log JSON entries."""
    return [
        json.dumps({
            "ts": 1710600000.0,
            "uid": "CYnvWc3enJjQC9w5y2",
            "id.orig_h": "192.168.1.42",
            "id.orig_p": 55432,
            "id.resp_h": "192.168.1.1",
            "id.resp_p": 22,
            "hassh": "ec7378c1a92f5a8dde7e8b7a1ddf33d1",
            "hasshServer": "b12d2871a1189eff20364cf5f4c3cc96",
        }),
    ]


@pytest.fixture
def sample_software_log_lines() -> list[str]:
    """Sample software.log JSON entries."""
    return [
        json.dumps({
            "ts": 1710600000.0,
            "host": "192.168.1.42",
            "software_type": "HTTP::BROWSER",
            "name": "ESP32-HTTPClient",
            "version.major": 1,
            "version.minor": 0,
        }),
        json.dumps({
            "ts": 1710600001.0,
            "host": "192.168.1.100",
            "software_type": "OS",
            "name": "Linux",
            "version.major": 5,
            "version.minor": 15,
        }),
    ]


@pytest.fixture
def mock_fingerprint_service() -> AsyncMock:
    """Mock FingerprintService for unit tests."""
    service = AsyncMock()
    service.get_by_ip = AsyncMock(return_value=None)
    service.get_discovered = AsyncMock(return_value=[])
    service.get_new_devices = AsyncMock(return_value=[])
    return service
