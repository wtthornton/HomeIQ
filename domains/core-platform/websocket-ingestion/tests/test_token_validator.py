"""
Tests for Token Validator
"""

from src.token_validator import TokenValidator


class TestTokenValidator:
    """Test cases for TokenValidator class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.validator = TokenValidator()

    def test_valid_token(self):
        """Test validation of valid token"""
        valid_token = "abcdefghijklmnopqrstuvwxyz123456"
        is_valid, error_msg = self.validator.validate_token(valid_token)

        assert is_valid is True
        assert error_msg == ""

    def test_empty_token(self):
        """Test validation of empty token"""
        is_valid, error_msg = self.validator.validate_token("")

        assert is_valid is False
        assert "empty" in error_msg.lower()

    def test_none_token(self):
        """Test validation of None token"""
        is_valid, error_msg = self.validator.validate_token(None)

        assert is_valid is False
        assert "empty" in error_msg.lower()

    def test_short_token(self):
        """Test validation of token that's too short"""
        short_token = "abc123"
        is_valid, error_msg = self.validator.validate_token(short_token)

        assert is_valid is False
        assert "too short" in error_msg.lower()

    def test_long_token(self):
        """Test validation of token that's too long"""
        long_token = "a" * 200  # Exceeds max_length
        is_valid, error_msg = self.validator.validate_token(long_token)

        assert is_valid is False
        assert "too long" in error_msg.lower()

    def test_invalid_characters(self):
        """Test validation of token with invalid characters"""
        invalid_token = "abc123!@#$%^&*()abcdefghijklmnopqrstuvwxyz"  # Make it long enough
        is_valid, error_msg = self.validator.validate_token(invalid_token)

        assert is_valid is False
        assert "invalid characters" in error_msg.lower()

    def test_token_with_spaces(self):
        """Test validation of token with spaces"""
        token_with_spaces = "abc def ghi jkl mno pqr stu vwx yz1 234"
        is_valid, error_msg = self.validator.validate_token(token_with_spaces)

        assert is_valid is False
        assert "invalid characters" in error_msg.lower()

    def test_token_with_hyphens(self):
        """Test validation of token with hyphens"""
        token_with_hyphens = "abc-def-ghi-jkl-mno-pqr-stu-vwx-yz1-234"
        is_valid, error_msg = self.validator.validate_token(token_with_hyphens)

        assert is_valid is False
        assert "invalid characters" in error_msg.lower()

    def test_minimum_length_token(self):
        """Test validation of token with minimum length"""
        min_token = "a" * 32  # Exactly minimum length
        is_valid, error_msg = self.validator.validate_token(min_token)

        assert is_valid is True
        assert error_msg == ""

    def test_maximum_length_token(self):
        """Test validation of token with maximum length"""
        max_token = "a" * 128  # Exactly maximum length
        is_valid, error_msg = self.validator.validate_token(max_token)

        assert is_valid is True
        assert error_msg == ""

    def test_mask_token(self):
        """Test token masking functionality"""
        token = "abcdefghijklmnopqrstuvwxyz123456"
        masked = self.validator.mask_token(token)

        assert masked == "****************************3456"
        assert len(masked) == len(token)
        assert masked.endswith("3456")

    def test_mask_short_token(self):
        """Test masking of short token"""
        short_token = "abc"
        masked = self.validator.mask_token(short_token)

        assert masked == "****"

    def test_mask_empty_token(self):
        """Test masking of empty token"""
        masked = self.validator.mask_token("")

        assert masked == "****"

    def test_get_token_info_valid(self):
        """Test getting token info for valid token"""
        token = "abcdefghijklmnopqrstuvwxyz123456"
        info = self.validator.get_token_info(token)

        assert info["is_valid"] is True
        assert info["error_message"] is None
        assert info["length"] == len(token)
        assert info["masked_token"] == "****************************3456"
        assert "validation_timestamp" in info

    def test_get_token_info_invalid(self):
        """Test getting token info for invalid token"""
        token = "short"
        info = self.validator.get_token_info(token)

        assert info["is_valid"] is False
        assert info["error_message"] is not None
        assert info["length"] == len(token)
        assert info["masked_token"] == "*hort"
        assert "validation_timestamp" in info

    def test_token_format_validation(self):
        """Test token format validation directly"""
        validator = TokenValidator()

        # Valid format
        is_valid, error_msg = validator.validate_token_format("abcdefghijklmnopqrstuvwxyz123456")
        assert is_valid is True
        assert error_msg == ""

        # Invalid format - too short
        is_valid, error_msg = validator.validate_token_format("short")
        assert is_valid is False
        assert "too short" in error_msg.lower()

        # Invalid format - invalid characters
        is_valid, error_msg = validator.validate_token_format("abc!@#abcdefghijklmnopqrstuvwxyz123456")
        assert is_valid is False
        assert "invalid characters" in error_msg.lower()
