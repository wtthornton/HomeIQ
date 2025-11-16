"""
Static code validation prior to sandbox execution.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Set

FORBIDDEN_NAMES = {
    "__subclasses__",
    "__bases__",
    "__mro__",
    "__globals__",
    "__getattribute__",
    "__setattr__",
    "__dict__",
    "__class__",
    "__builtins__",
    "__import__",
    "globals",
    "locals",
    "vars",
    "dir",
    "eval",
    "exec",
    "compile",
    "open",
    "input",
    "help",
    "os",
    "sys",
    "subprocess",
}


class CodeValidationError(ValueError):
    """Raised when incoming code violates safety policy."""


@dataclass
class CodeValidatorConfig:
    """Configuration for code validator thresholds."""

    max_bytes: int
    max_ast_nodes: int
    allowed_imports: Set[str]


class CodeValidator:
    """Performs structural validation on user-submitted code strings."""

    def __init__(self, config: CodeValidatorConfig):
        self.config = config

    def validate(self, code: str) -> None:
        """Validate code string raises CodeValidationError when unsafe."""
        if not code or not code.strip():
            raise CodeValidationError("Code payload is empty")

        self._enforce_size_limit(code)
        tree = self._parse_ast(code)
        self._enforce_node_limit(tree)
        self._enforce_import_whitelist(tree)
        self._enforce_forbidden_names(tree)

    def _enforce_size_limit(self, code: str) -> None:
        byte_len = len(code.encode("utf-8"))
        if byte_len > self.config.max_bytes:
            raise CodeValidationError(
                f"Code payload is {byte_len} bytes; limit is {self.config.max_bytes} bytes"
            )

    def _parse_ast(self, code: str) -> ast.AST:
        try:
            return ast.parse(code, mode="exec", type_comments=True)
        except SyntaxError as exc:
            raise CodeValidationError(f"Code failed to parse: {exc.msg}") from exc

    def _enforce_node_limit(self, tree: ast.AST) -> None:
        node_count = sum(1 for _ in ast.walk(tree))
        if node_count > self.config.max_ast_nodes:
            raise CodeValidationError(
                f"Code is too complex ({node_count} AST nodes); limit is {self.config.max_ast_nodes}"
            )

    def _enforce_import_whitelist(self, tree: ast.AST) -> None:
        allowed = self.config.allowed_imports

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root not in allowed:
                        raise CodeValidationError(f"Import of '{root}' is not permitted")
            elif isinstance(node, ast.ImportFrom):
                if node.level and node.level > 0:
                    raise CodeValidationError("Relative imports are not permitted")
                module = (node.module or "").split(".")[0]
                if module and module not in allowed:
                    raise CodeValidationError(f"Import of '{module}' is not permitted")

    def _enforce_forbidden_names(self, tree: ast.AST) -> None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
                raise CodeValidationError(f"Use of '{node.id}' is not allowed in sandbox")
            if isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_NAMES:
                raise CodeValidationError(f"Attribute '{node.attr}' is not allowed in sandbox")
