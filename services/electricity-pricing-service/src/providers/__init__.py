"""Electricity Pricing Providers"""


class ProviderError(Exception):
    """Base exception for provider errors"""
    pass


class ProviderAPIError(ProviderError):
    """Exception for API HTTP errors"""
    def __init__(self, status_code: int, message: str = ""):
        self.status_code = status_code
        super().__init__(message or f"API returned status {status_code}")


class ProviderParseError(ProviderError):
    """Exception for response parsing errors"""
    pass


from .awattar import AwattarProvider

__all__ = ['AwattarProvider', 'ProviderError', 'ProviderAPIError', 'ProviderParseError']

