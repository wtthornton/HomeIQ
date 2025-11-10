"""
LangChain integration helpers for AI Automation Service.

These modules provide optional prototypes that leverage LangChain building
blocks without disrupting existing code paths. They are enabled behind feature
flags defined in `config.py` so the default single-home deployment remains
lightweight.
"""

__all__ = ["ask_ai_chain", "pattern_chain"]


