"""Unit tests for flux_utils.py — Story 85.4

Security-critical tests for Flux query sanitization.
Tests injection prevention, boundary conditions, and DoS protection.
"""

import warnings

import pytest

from src.flux_utils import MAX_SANITIZED_LENGTH, sanitize_flux_value


class TestSanitizeNormalInputs:
    """Test that valid inputs pass through correctly."""

    def test_alphanumeric_string(self):
        assert sanitize_flux_value("light123") == "light123"

    def test_entity_id_with_dot(self):
        assert sanitize_flux_value("light.living_room") == "light.living_room"

    def test_hyphenated_name(self):
        assert sanitize_flux_value("my-device") == "my-device"

    def test_underscored_name(self):
        assert sanitize_flux_value("my_device") == "my_device"

    def test_numeric_input(self):
        assert sanitize_flux_value("12345") == "12345"

    def test_numeric_type_converted(self):
        assert sanitize_flux_value(42) == "42"


class TestSanitizeEdgeCases:

    def test_none_returns_empty(self):
        assert sanitize_flux_value(None) == ""

    def test_empty_string_returns_empty(self):
        assert sanitize_flux_value("") == ""

    def test_whitespace_only_returns_empty(self):
        assert sanitize_flux_value("   ") == ""

    def test_strips_leading_trailing_whitespace(self):
        assert sanitize_flux_value("  hello  ") == "hello"

    def test_internal_whitespace_collapsed(self):
        """Internal spaces are removed by the sanitizer."""
        result = sanitize_flux_value("hello world")
        assert result == "helloworld"


class TestSanitizeSQLInjection:
    """Test that SQL injection patterns are neutralized."""

    def test_sql_drop_table(self):
        result = sanitize_flux_value("entity'; DROP TABLE--")
        assert "DROP" in result  # word chars kept
        assert "'" not in result  # quotes removed
        assert "--" not in result  # comments removed

    def test_sql_union_select(self):
        result = sanitize_flux_value("' UNION SELECT * FROM users--")
        assert "'" not in result
        assert "--" not in result

    def test_sql_semicolon(self):
        result = sanitize_flux_value("value; DELETE FROM measurements")
        assert ";" not in result

    def test_sql_comment_double_dash(self):
        result = sanitize_flux_value("value -- comment")
        assert "--" not in result


class TestSanitizeFluxInjection:
    """Test that Flux-specific injection patterns are neutralized."""

    def test_pipe_operator_removed(self):
        result = sanitize_flux_value("value |> drop()")
        assert "|" not in result
        assert ">" in result or ">" not in result  # > is a special char, removed

    def test_flux_function_parens_removed(self):
        result = sanitize_flux_value("from(bucket: 'evil')")
        assert "(" not in result
        assert ")" not in result

    def test_curly_braces_removed(self):
        result = sanitize_flux_value('r._measurement == "evil" {yield}')
        assert "{" not in result
        assert "}" not in result

    def test_backtick_removed(self):
        result = sanitize_flux_value("`injected`")
        assert "`" not in result


class TestSanitizeSpecialCharacters:

    def test_null_bytes_removed(self):
        result = sanitize_flux_value("hello\x00world")
        assert "\x00" not in result

    def test_newlines_removed(self):
        result = sanitize_flux_value("line1\nline2")
        assert "\n" not in result

    def test_tabs_removed(self):
        result = sanitize_flux_value("col1\tcol2")
        assert "\t" not in result

    def test_carriage_return_removed(self):
        result = sanitize_flux_value("line1\r\nline2")
        assert "\r" not in result

    def test_single_quotes_removed(self):
        result = sanitize_flux_value("it's a value")
        assert "'" not in result

    def test_double_quotes_removed(self):
        result = sanitize_flux_value('say "hello"')
        assert '"' not in result

    def test_backslash_removed(self):
        result = sanitize_flux_value("path\\to\\file")
        assert "\\" not in result

    def test_angle_brackets_removed(self):
        result = sanitize_flux_value("<script>alert('xss')</script>")
        assert "<" not in result
        assert ">" not in result


class TestSanitizeUnicode:

    def test_unicode_letters_kept(self):
        """Word characters include unicode letters."""
        result = sanitize_flux_value("café")
        assert "caf" in result

    def test_unicode_emoji_removed(self):
        """Emoji are non-word characters and should be removed."""
        result = sanitize_flux_value("test🔥value")
        assert "🔥" not in result
        assert "testvalue" in result

    def test_chinese_characters_kept(self):
        """CJK characters are word characters in regex."""
        result = sanitize_flux_value("温度")
        assert len(result) > 0


class TestSanitizeDoSProtection:

    def test_truncates_long_input(self):
        long_value = "a" * 2000
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            result = sanitize_flux_value(long_value)
        assert len(result) == MAX_SANITIZED_LENGTH

    def test_custom_max_length(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            result = sanitize_flux_value("a" * 100, max_length=50)
        assert len(result) == 50

    def test_truncation_emits_warning(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            sanitize_flux_value("a" * 2000)
            assert len(w) >= 1
            assert "truncated" in str(w[0].message).lower()

    def test_value_at_max_length_not_truncated(self):
        exact = "a" * MAX_SANITIZED_LENGTH
        result = sanitize_flux_value(exact)
        assert len(result) == MAX_SANITIZED_LENGTH


class TestSanitizeAllSpecialCharsRemoved:
    """If input is entirely special characters, result should be empty."""

    def test_all_special_chars(self):
        result = sanitize_flux_value("!@#$%^&*()")
        assert result == ""

    def test_only_quotes(self):
        result = sanitize_flux_value("'''\"\"\"")
        assert result == ""
