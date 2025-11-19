"""
Action Execution Exceptions

Custom exceptions for action execution engine.
Uses shared exception hierarchy from shared/exceptions.py
"""

import sys
import os
from pathlib import Path

# Add shared directory to path for imports
shared_path_override = os.getenv('HOMEIQ_SHARED_PATH')
try:
    app_root = Path(__file__).resolve().parents[5]  # Go up to project root
except Exception:
    app_root = Path("/app")

candidate_paths = []
if shared_path_override:
    candidate_paths.append(Path(shared_path_override).expanduser())
candidate_paths.extend([
    app_root / "shared",
    Path("/app/shared"),
    Path.cwd() / "shared",
    Path(__file__).parent.parent.parent.parent.parent.parent / "shared",  # Fallback for local dev
])

shared_path = None
for p in candidate_paths:
    if p.exists():
        shared_path = p.resolve()
        break

if shared_path and str(shared_path) not in sys.path:
    sys.path.insert(0, str(shared_path))

from exceptions import ServiceError, ValidationError, NetworkError


class ActionExecutionError(ServiceError):
    """Base exception for action execution failures"""
    pass


class ServiceCallError(NetworkError):
    """HTTP service call failures"""
    
    def __init__(self, message: str, status_code: int = None, response_data: dict = None, context: dict = None):
        super().__init__(message, context=context)
        self.status_code = status_code
        self.response_data = response_data
        if context is None:
            self.context = {}
        if status_code:
            self.context["status_code"] = status_code
        if response_data:
            self.context["response_data"] = response_data


class ActionParseError(ValidationError):
    """YAML parsing failures"""
    pass


class RetryExhaustedError(ServiceError):
    """All retries failed"""
    
    def __init__(self, message: str, attempts: int = None, last_error: Exception = None, context: dict = None):
        ctx = context or {}
        if attempts is not None:
            ctx["attempts"] = attempts
        if last_error:
            ctx["last_error"] = str(last_error)
        super().__init__(message, context=ctx)
        self.attempts = attempts
        self.last_error = last_error


class InvalidActionError(ValidationError):
    """Invalid action structure or format"""
    pass

