"""
Unit tests for CodeValidator.

Tests code validation logic including size limits, AST parsing, import whitelisting,
and forbidden name detection.
"""

import pytest

from src.security.code_validator import (
    CodeValidationError,
    CodeValidator,
    CodeValidatorConfig,
)


@pytest.fixture
def validator():
    """Create a CodeValidator instance for testing."""
    config = CodeValidatorConfig(
        max_bytes=1000,
        max_ast_nodes=100,
        allowed_imports={"json", "math", "datetime"},
    )
    return CodeValidator(config)


class TestCodeValidator:
    """Test suite for CodeValidator."""

    def test_validate_empty_code(self, validator):
        """Test that empty code raises CodeValidationError."""
        with pytest.raises(CodeValidationError, match="Code payload is empty"):
            validator.validate("")
        
        with pytest.raises(CodeValidationError, match="Code payload is empty"):
            validator.validate("   \n\t  ")

    def test_validate_size_limit(self, validator):
        """Test that code exceeding size limit raises error."""
        large_code = "x" * 1001
        with pytest.raises(CodeValidationError, match="Code payload is .* bytes; limit is 1000 bytes"):
            validator.validate(large_code)

    def test_validate_size_limit_unicode(self, validator):
        """Test that unicode characters are counted correctly."""
        # Each emoji is typically 4 bytes in UTF-8
        unicode_code = "🚀" * 300  # 1200 bytes
        with pytest.raises(CodeValidationError):
            validator.validate(unicode_code)

    def test_validate_syntax_error(self, validator):
        """Test that invalid syntax raises CodeValidationError."""
        invalid_code = "def invalid syntax here"
        with pytest.raises(CodeValidationError, match="Code failed to parse"):
            validator.validate(invalid_code)

    def test_validate_ast_node_limit(self, validator):
        """Test that code exceeding AST node limit raises error."""
        # Create code with many nodes (nested loops, conditions, etc.)
        complex_code = "\n".join([f"x{i} = {i}" for i in range(150)])
        with pytest.raises(CodeValidationError, match="Code is too complex"):
            validator.validate(complex_code)

    def test_validate_allowed_import(self, validator):
        """Test that allowed imports pass validation."""
        code = "import json\nresult = json.dumps({'key': 'value'})\n_ = result"
        # Should not raise
        validator.validate(code)

    def test_validate_forbidden_import(self, validator):
        """Test that forbidden imports raise error."""
        code = "import os\nresult = os.getcwd()\n_ = result"
        with pytest.raises(CodeValidationError, match="Import of 'os' is not permitted"):
            validator.validate(code)

    def test_validate_relative_import(self, validator):
        """Test that relative imports are blocked."""
        code = "from . import module"
        with pytest.raises(CodeValidationError, match="Relative imports are not permitted"):
            validator.validate(code)

    def test_validate_import_from_allowed(self, validator):
        """Test that allowed import from passes."""
        code = "from json import loads, dumps\nresult = loads('{}')\n_ = result"
        validator.validate(code)

    def test_validate_import_from_forbidden(self, validator):
        """Test that forbidden import from raises error."""
        code = "from sys import exit"
        with pytest.raises(CodeValidationError, match="Import of 'sys' is not permitted"):
            validator.validate(code)

    def test_validate_forbidden_name(self, validator):
        """Test that forbidden names raise error."""
        forbidden_names = ["eval", "exec", "open", "__import__", "__builtins__"]
        for name in forbidden_names:
            code = f"result = {name}\n_ = result"
            with pytest.raises(CodeValidationError, match=f"Use of '{name}' is not allowed"):
                validator.validate(code)

    def test_validate_forbidden_attribute(self, validator):
        """Test that forbidden attributes raise error."""
        code = "result = obj.__dict__\n_ = result"
        with pytest.raises(CodeValidationError, match="Attribute '__dict__' is not allowed"):
            validator.validate(code)

    def test_validate_safe_code(self, validator):
        """Test that safe code passes validation."""
        safe_code = """
result = 2 + 2
data = [1, 2, 3, 4, 5]
sum_data = sum(data)
_ = sum_data
"""
        validator.validate(safe_code)

    def test_validate_with_math_import(self, validator):
        """Test that math import is allowed."""
        code = "import math\nresult = math.sqrt(16)\n_ = result"
        validator.validate(code)

    def test_validate_with_datetime_import(self, validator):
        """Test that datetime import is allowed."""
        code = "import datetime\nnow = datetime.datetime.now()\n_ = now"
        validator.validate(code)

    def test_validate_nested_imports(self, validator):
        """Test validation with nested import statements."""
        code = """
import json
import math
result = json.dumps({'value': math.pi})
_ = result
"""
        validator.validate(code)

    def test_validate_complex_but_valid_code(self, validator):
        """Test validation of complex but valid code."""
        code = """
def calculate(n):
    if n <= 0:
        return 0
    result = 0
    for i in range(n):
        result += i * i
    return result

_ = calculate(10)
"""
        validator.validate(code)

    def test_validate_multiline_code(self, validator):
        """Test validation of multiline code."""
        code = """
# This is a comment
x = 1
y = 2
z = x + y
_ = z
"""
        validator.validate(code)

    def test_validate_with_strings(self, validator):
        """Test validation with string literals."""
        code = """
text = "Hello, World!"
length = len(text)
_ = length
"""
        validator.validate(code)

    def test_validate_list_comprehension(self, validator):
        """Test validation with list comprehensions."""
        code = """
squares = [x * x for x in range(10)]
_ = squares
"""
        validator.validate(code)

    def test_validate_dict_comprehension(self, validator):
        """Test validation with dict comprehensions."""
        code = """
mapping = {x: x * 2 for x in range(5)}
_ = mapping
"""
        validator.validate(code)

    def test_validate_with_conditionals(self, validator):
        """Test validation with conditional statements."""
        code = """
x = 10
if x > 5:
    result = "large"
else:
    result = "small"
_ = result
"""
        validator.validate(code)

    def test_validate_with_loops(self, validator):
        """Test validation with loops."""
        code = """
numbers = []
for i in range(5):
    numbers.append(i * 2)
_ = numbers
"""
        validator.validate(code)

    def test_validate_with_functions(self, validator):
        """Test validation with function definitions."""
        code = """
def add(a, b):
    return a + b

result = add(3, 4)
_ = result
"""
        validator.validate(code)

    def test_validate_edge_case_single_char(self, validator):
        """Test validation with single character code."""
        code = "_ = 1"
        validator.validate(code)

    def test_validate_edge_case_exact_size_limit(self, validator):
        """Test validation at exact size limit."""
        code = "x" * 1000
        validator.validate(code)

    def test_validate_edge_case_exact_ast_limit(self, validator):
        """Test validation at exact AST node limit."""
        # Create code with exactly 100 nodes
        code = "\n".join([f"x{i} = {i}" for i in range(50)])  # ~50 nodes
        validator.validate(code)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

