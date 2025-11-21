"""
Token Validation System for Home Assistant Authentication
"""

import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)


class TokenValidator:
    """Validates Home Assistant long-lived access tokens"""

    def __init__(self):
        # Home Assistant token format: JWT tokens can be quite long (200+ characters)
        # Support both traditional tokens and JWT format tokens
        self.token_pattern = re.compile(r"^[a-zA-Z0-9._-]+$")
        self.min_length = 32
        self.max_length = 300  # Increased to support JWT tokens

    def validate_token_format(self, token: str) -> tuple[bool, str]:
        """
        Validate token format

        Args:
            token: The token to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not token:
            return False, "Token is empty"

        if not isinstance(token, str):
            return False, "Token must be a string"

        if len(token) < self.min_length:
            return False, f"Token too short (minimum {self.min_length} characters)"

        if len(token) > self.max_length:
            return False, f"Token too long (maximum {self.max_length} characters)"

        if not self.token_pattern.match(token):
            return False, "Token contains invalid characters (must be alphanumeric)"

        return True, ""

    def mask_token(self, token: str) -> str:
        """
        Mask token for logging (show only last 4 characters)

        Args:
            token: The token to mask

        Returns:
            Masked token string
        """
        if not token or len(token) < 4:
            return "****"

        return f"{'*' * (len(token) - 4)}{token[-4:]}"

    def validate_token(self, token: str) -> tuple[bool, str]:
        """
        Complete token validation

        Args:
            token: The token to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        logger.debug(f"Validating token: {self.mask_token(token)}")

        # Format validation
        is_valid, error_msg = self.validate_token_format(token)
        if not is_valid:
            logger.warning(f"Token validation failed: {error_msg}")
            return False, error_msg

        logger.info(f"Token validation successful: {self.mask_token(token)}")
        return True, ""

    def get_token_info(self, token: str) -> dict:
        """
        Get information about the token

        Args:
            token: The token to analyze

        Returns:
            Dictionary with token information
        """
        is_valid, error_msg = self.validate_token(token)

        return {
            "is_valid": is_valid,
            "error_message": error_msg if not is_valid else None,
            "length": len(token) if token else 0,
            "masked_token": self.mask_token(token) if token else "****",
            "validation_timestamp": datetime.now().isoformat(),
        }
