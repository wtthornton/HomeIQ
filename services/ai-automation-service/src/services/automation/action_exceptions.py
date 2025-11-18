"""
Action Execution Exceptions

Custom exceptions for action execution engine.
"""


class ActionExecutionError(Exception):
    """Base exception for action execution failures"""
    pass


class ServiceCallError(ActionExecutionError):
    """HTTP service call failures"""
    
    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class ActionParseError(ActionExecutionError):
    """YAML parsing failures"""
    pass


class RetryExhaustedError(ActionExecutionError):
    """All retries failed"""
    
    def __init__(self, message: str, attempts: int = None, last_error: Exception = None):
        super().__init__(message)
        self.attempts = attempts
        self.last_error = last_error


class InvalidActionError(ActionExecutionError):
    """Invalid action structure or format"""
    pass

