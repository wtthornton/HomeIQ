"""Health check script - exits 0 if service is running (200 or 503 degraded)."""

import sys
import urllib.error
import urllib.request

_PORT = 8036
_TIMEOUT = 5

try:
    port = int(__import__("os").environ.get("ACTIVITY_RECOGNITION_PORT", _PORT))
except (TypeError, ValueError):
    port = _PORT

try:
    urllib.request.urlopen(
        f"http://localhost:{port}/api/v1/health",
        timeout=_TIMEOUT,
    )
    sys.exit(0)
except urllib.error.HTTPError as e:
    # 503 = degraded (no model loaded) but service is running
    sys.exit(0 if e.code == 503 else 1)
except Exception:
    sys.exit(1)
