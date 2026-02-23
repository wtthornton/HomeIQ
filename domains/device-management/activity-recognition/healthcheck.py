"""Health check script - exits 0 if service is running (200 or 503 degraded)."""

import os
import sys
import urllib.error
import urllib.request

_PORT = 8036
_TIMEOUT = 5


def _get_port() -> int:
    """Return port from env or default."""
    try:
        return int(os.environ.get("ACTIVITY_RECOGNITION_PORT", _PORT))
    except (TypeError, ValueError):
        return _PORT


def main() -> None:
    """Check service health; exit 0 if up (200 or 503), else 1."""
    port = _get_port()
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


if __name__ == "__main__":
    main()
