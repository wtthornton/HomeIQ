"""
Miner Module

Contains crawler, parser, and storage components for automation mining.
"""

from .discourse_client import DiscourseClient
from .parser import AutomationParser
from .repository import CorpusRepository

__all__ = ["AutomationParser", "CorpusRepository", "DiscourseClient"]

