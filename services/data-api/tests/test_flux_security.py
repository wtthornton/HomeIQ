"""
Security tests for Flux query sanitization.

Tests SQL/Flux injection prevention and input validation.
"""

import pytest

from src.flux_utils import sanitize_flux_value, MAX_SANITIZED_LENGTH


class TestFluxSanitization:
    """Test suite for Flux value sanitization."""

    def test_basic_sanitization(self):
        """Test basic sanitization of normal values."""
        assert sanitize_flux_value("light.living_room") == "light.living_room"
        assert sanitize_flux_value("sensor.temperature") == "sensor.temperature"
        assert sanitize_flux_value("switch-1") == "switch-1"

    def test_sql_injection_prevention(self):
        """Test that SQL injection attempts are blocked."""
        # Common SQL injection patterns
        injection_attempts = [
            ("entity'; DROP TABLE events--", ["DROP"]),
            ("entity' OR '1'='1", []),
            ("entity'; DELETE FROM events--", ["DELETE"]),
            ("entity' UNION SELECT * FROM events--", []),
        ]

        for attempt, preserved_words in injection_attempts:
            sanitized = sanitize_flux_value(attempt)
            # Should not contain SQL injection characters
            assert "'" not in sanitized or sanitized.count("'") == sanitized.count("\\'")
            assert ";" not in sanitized
            assert "--" not in sanitized
            for word in preserved_words:
                assert word in sanitized  # keyword preserved but injection removed

    def test_flux_injection_prevention(self):
        """Test that Flux injection attempts are blocked."""
        # Flux-specific injection patterns
        flux_injections = [
            'entity" |> filter(fn: (r) => r._value == "injected")',
            'entity" |> drop()',
            'entity" |> limit(n: 1000000)',
        ]
        
        for injection in flux_injections:
            sanitized = sanitize_flux_value(injection)
            # Should not contain unescaped quotes or pipe operators
            assert '|>' not in sanitized
            assert sanitized.count('"') == sanitized.count('\\"') or '"' not in sanitized

    def test_special_characters(self):
        """Test handling of special characters."""
        test_cases = [
            ("test@example.com", "testexample.com"),  # @ removed, . kept for entity_ids
            ("test#123", "test123"),  # # removed
            ("test$value", "testvalue"),  # $ removed
            ("test%20encoded", "test20encoded"),  # % removed
            ("test&value", "testvalue"),  # & removed
        ]

        for input_val, expected in test_cases:
            sanitized = sanitize_flux_value(input_val)
            assert sanitized == expected

    def test_quote_escaping(self):
        """Test that quotes are removed (injection-safe; escaping happens only if kept)."""
        # Implementation removes ', " in the allowed-char filter for safety
        assert sanitize_flux_value('test"value') == 'testvalue'
        assert sanitize_flux_value("test'value") == "testvalue"
        assert sanitize_flux_value('test"value"') == 'testvalue'

    def test_length_limiting(self):
        """Test that length limits are enforced."""
        long_value = "x" * (MAX_SANITIZED_LENGTH + 100)
        sanitized = sanitize_flux_value(long_value)
        assert len(sanitized) <= MAX_SANITIZED_LENGTH

    def test_none_handling(self):
        """Test handling of None values."""
        assert sanitize_flux_value(None) == ""
        assert sanitize_flux_value("") == ""

    def test_whitespace_handling(self):
        """Test handling of whitespace."""
        assert sanitize_flux_value("  test  ") == "test"
        assert sanitize_flux_value("test\nvalue") == "testvalue"
        assert sanitize_flux_value("test\tvalue") == "testvalue"

    def test_unicode_handling(self):
        """Test handling of unicode characters."""
        # Unicode should be preserved if it's word characters
        assert sanitize_flux_value("café") == "café"
        assert sanitize_flux_value("тест") == "тест"
        
        # Special unicode should be removed
        assert sanitize_flux_value("test\u0000null") == "testnull"

    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        # Empty after sanitization
        assert sanitize_flux_value("!!!") == ""
        assert sanitize_flux_value("###") == ""
        
        # Only special characters
        assert sanitize_flux_value("';--") == ""
        
        # Mixed case
        assert sanitize_flux_value("Test_Value-123") == "Test_Value-123"

    def test_custom_max_length(self):
        """Test custom max length parameter."""
        long_value = "x" * 500
        sanitized = sanitize_flux_value(long_value, max_length=100)
        assert len(sanitized) <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

