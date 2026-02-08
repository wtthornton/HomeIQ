"""Health check script - exits 0 if service is running (200 or 503 degraded)."""
import urllib.request
import urllib.error
import sys

try:
    urllib.request.urlopen("http://localhost:8036/api/v1/health")
    sys.exit(0)
except urllib.error.HTTPError as e:
    # 503 = degraded (no model loaded) but service is running
    sys.exit(0 if e.code == 503 else 1)
except Exception:
    sys.exit(1)
