"""
Approval Command Recognition Service

2025 Preview-and-Approval Workflow: Recognizes user approval commands
"""

import logging
import re
from typing import Literal

logger = logging.getLogger(__name__)

# Approval command patterns (case-insensitive)
APPROVAL_PATTERNS = [
    r"\bapprove\b",
    r"\bcreate\b",
    r"\bexecute\b",
    r"\byes\b",
    r"\bgo ahead\b",
    r"\bproceed\b",
    r"\bdo it\b",
    r"\bmake it\b",
    r"\bdo that\b",
    r"\bthat's good\b",
    r"\bthat works\b",
    r"\bsounds good\b",
    r"\bthat's fine\b",
    r"\bthat's perfect\b",
    r"\bgo for it\b",
    r"\bdo that\b",
]

# Rejection/cancellation patterns
REJECTION_PATTERNS = [
    r"\bcancel\b",
    r"\bno\b",
    r"\bdon't\b",
    r"\bdon't create\b",
    r"\bdon't do it\b",
    r"\bdon't make\b",
    r"\bnever mind\b",
    r"\bforget it\b",
    r"\bnot now\b",
    r"\bnot yet\b",
    r"\bwait\b",
    r"\bstop\b",
]


def recognize_approval_intent(message: str) -> Literal["approve", "reject", "unclear"]:
    """
    Recognize user intent from message (approve, reject, or unclear).

    Args:
        message: User message to analyze

    Returns:
        "approve" if message indicates approval
        "reject" if message indicates rejection/cancellation
        "unclear" if intent cannot be determined
    """
    if not message or not message.strip():
        return "unclear"

    message_lower = message.lower().strip()

    # Check for rejection patterns first (higher priority)
    for pattern in REJECTION_PATTERNS:
        if re.search(pattern, message_lower, re.IGNORECASE):
            logger.debug(f"Rejection pattern matched: '{pattern}' in message: {message[:100]}")
            return "reject"

    # Check for approval patterns
    for pattern in APPROVAL_PATTERNS:
        if re.search(pattern, message_lower, re.IGNORECASE):
            logger.debug(f"Approval pattern matched: '{pattern}' in message: {message[:100]}")
            return "approve"

    # If message is very short and contains only "yes" or "no", treat as approval/rejection
    if message_lower in ["yes", "y", "ok", "okay"]:
        return "approve"
    if message_lower in ["no", "n"]:
        return "reject"

    # If message contains refinement requests (change, modify, update, etc.), it's unclear
    refinement_keywords = ["change", "modify", "update", "adjust", "fix", "different", "instead", "rather"]
    if any(keyword in message_lower for keyword in refinement_keywords):
        logger.debug(f"Refinement keywords detected in message: {message[:100]}")
        return "unclear"

    return "unclear"


def is_approval_command(message: str) -> bool:
    """
    Check if message is an approval command.

    Args:
        message: User message to check

    Returns:
        True if message indicates approval
    """
    return recognize_approval_intent(message) == "approve"


def is_rejection_command(message: str) -> bool:
    """
    Check if message is a rejection/cancellation command.

    Args:
        message: User message to check

    Returns:
        True if message indicates rejection
    """
    return recognize_approval_intent(message) == "reject"

