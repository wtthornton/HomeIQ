"""Suite-wide pytest hooks for automation-domain.

The three slices are one process now (TAP-7275), so any slice's tests that
import ``src.main`` load the merged app and run the merged lifespan. That
lifespan refuses to start without a non-empty ``AGENTFORGE_API_KEY`` -- chat is
an AgentForge workflow run, and a container that boots without the credential
would report healthy with a broken ``/api/v1/chat``. CI and local runs have no
``.env``, so the default belongs here, above all three slices, rather than in
one slice's conftest.
"""

from __future__ import annotations

import os

if not os.environ.get("AGENTFORGE_API_KEY", "").strip():
    os.environ["AGENTFORGE_API_KEY"] = "afp-test-not-real-key-for-pytest"
