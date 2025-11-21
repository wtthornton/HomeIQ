"""
Intent Matcher

Matches user intent from queries.
Determines if query is for automation, immediate action, or information.

Created: Phase 2 - Core Service Refactoring
"""

import logging
import re
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    """Types of user intents"""
    AUTOMATION = "automation"  # Create automation
    ACTION = "action"  # Immediate action (turn on lights)
    INFORMATION = "information"  # Query information
    CLARIFICATION = "clarification"  # Answer clarification question
    UNKNOWN = "unknown"


class IntentMatcher:
    """
    Matches user intent from natural language queries.

    Determines if the user wants to:
    - Create an automation
    - Execute an immediate action
    - Get information
    - Answer clarification questions
    """

    def __init__(self):
        """Initialize intent matcher"""
        # Intent keywords
        self.automation_keywords = [
            "automate", "automatic", "schedule", "routine", "when", "if",
            "create automation", "make automation", "set up automation",
        ]

        self.action_keywords = [
            "turn on", "turn off", "switch", "control", "set", "activate",
            "deactivate", "open", "close", "lock", "unlock",
        ]

        self.information_keywords = [
            "what", "show", "tell", "list", "get", "find", "check",
            "status", "state", "how many", "which",
        ]

        logger.info("IntentMatcher initialized")

    def match_intent(self, query: str, context: dict[str, Any] | None = None) -> IntentType:
        """
        Match intent from query.

        Args:
            query: User query string
            context: Optional conversation context

        Returns:
            IntentType enum value
        """
        query_lower = query.lower()

        # Check for clarification (answers to questions)
        if context and context.get("clarification_questions"):
            # If there are pending clarification questions, likely an answer
            if any(keyword in query_lower for keyword in ["yes", "no", "the", "this", "that", "these", "those"]):
                return IntentType.CLARIFICATION

        # Check for immediate actions (imperative verbs)
        action_patterns = [
            r"\b(turn on|turn off|switch|set|activate|deactivate)\b",
            r"\b(open|close|lock|unlock)\b",
            r"^(turn|switch|set|activate|deactivate|open|close|lock|unlock)",
        ]

        for pattern in action_patterns:
            if re.search(pattern, query_lower):
                # Check if it's not automation-related
                if not any(kw in query_lower for kw in ["when", "if", "automation", "schedule"]):
                    return IntentType.ACTION

        # Check for automation keywords
        if any(keyword in query_lower for keyword in self.automation_keywords):
            return IntentType.AUTOMATION

        # Check for information queries
        if any(keyword in query_lower for keyword in self.information_keywords):
            return IntentType.INFORMATION

        # Default to automation for ambiguous queries
        return IntentType.AUTOMATION

    def get_intent_confidence(self, query: str, intent: IntentType) -> float:
        """
        Get confidence score for intent match.

        Args:
            query: User query
            intent: Matched intent

        Returns:
            Confidence score (0.0-1.0)
        """
        query_lower = query.lower()

        if intent == IntentType.ACTION:
            # High confidence if imperative verbs present
            if re.search(r"\b(turn on|turn off|switch|set)\b", query_lower):
                return 0.9
            return 0.7

        if intent == IntentType.AUTOMATION:
            # High confidence if automation keywords present
            if any(kw in query_lower for kw in ["automate", "automation", "schedule"]):
                return 0.9
            if any(kw in query_lower for kw in ["when", "if"]):
                return 0.8
            return 0.6

        if intent == IntentType.INFORMATION:
            # High confidence if question words present
            if any(kw in query_lower for kw in ["what", "show", "tell", "list"]):
                return 0.9
            return 0.7

        return 0.5

