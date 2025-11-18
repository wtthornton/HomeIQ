"""
Conversation Services Module

Manages conversation context, intent matching, and response building:
- Context Manager: Manages conversation context across turns
- Intent Matcher: Matches user intent (automation vs action vs information)
- Response Builder: Builds structured responses with response_type
- History Manager: Manages conversation history and context

Created: Phase 2 - Core Service Refactoring
"""

from .context_manager import ConversationContextManager
from .intent_matcher import IntentMatcher
from .response_builder import ResponseBuilder
from .history_manager import HistoryManager

__all__ = [
    'ConversationContextManager',
    'IntentMatcher',
    'ResponseBuilder',
    'HistoryManager'
]

