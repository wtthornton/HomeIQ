"""Pytest hooks for ha-ai-agent-service tests.

`main.py` instantiates Settings at import time and lifespan requires a non-empty
OPENAI_API_KEY. CI and local runs without .env must still load the app for ASGI tests.
"""
from __future__ import annotations

import os

if not os.environ.get("OPENAI_API_KEY", "").strip():
    os.environ["OPENAI_API_KEY"] = "sk-test-not-real-key-for-pytest"
