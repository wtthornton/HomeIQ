"""
Secure Python code execution sandbox for MCP code execution pattern.
NUC-optimized: Minimal resource overhead, single-process isolation.
"""

import asyncio
import contextlib
import importlib
import io
import json
import logging
import multiprocessing
import queue
import resource
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any

import psutil
from RestrictedPython import compile_restricted

logger = logging.getLogger(__name__)

SAFE_VALUE_TYPES = (str, int, float, bool, type(None))
MAX_CONTEXT_DEPTH = 4
MAX_CONTEXT_SIZE = 1024 * 1024  # 1MB max context size (JSON serialized)


def _safe_import_factory(allowed_modules: set[str]):
    """Build a safe __import__ implementation that enforces module whitelist."""

    allowed = set(allowed_modules)

    def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
        if level != 0:
            raise ImportError("Relative imports are not permitted inside the sandbox")

        root_name = name.split(".")[0]
        if root_name not in allowed:
            raise ImportError(f"Import '{root_name}' is not allowed in sandbox")

        module = importlib.import_module(name)

        if fromlist:
            for attr in fromlist:
                if attr.startswith("_"):
                    raise ImportError("Access to private attributes is blocked")

        return module

    return _safe_import


def _build_safe_builtins(allowed_imports: set[str]) -> MappingProxyType:
    """Create immutable mapping of safe builtins."""
    safe_import = _safe_import_factory(allowed_imports)
    builtins = {
        "print": print,
        "len": len,
        "range": range,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "list": list,
        "dict": dict,
        "set": set,
        "tuple": tuple,
        "frozenset": frozenset,
        "min": min,
        "max": max,
        "sum": sum,
        "sorted": sorted,
        "enumerate": enumerate,
        "zip": zip,
        "map": map,
        "filter": filter,
        "any": any,
        "all": all,
        "abs": abs,
        "round": round,
        "pow": pow,
        "reversed": reversed,
        "Exception": Exception,
        "ValueError": ValueError,
        "__import__": safe_import,
    }
    return MappingProxyType(builtins)


def _build_execution_env(context: dict[str, Any], allowed_imports: set[str]) -> dict[str, Any]:
    """Construct the execution globals for sandbox runs."""
    env: dict[str, Any] = {
        "__builtins__": _build_safe_builtins(allowed_imports),
        "__name__": "__sandbox__",
        "__package__": None,
    }
    env.update(context)
    return env


def _apply_resource_limits(config: dict[str, Any]):
    """Apply strict Linux resource limits inside sandbox process."""
    # These limits are only enforced on Linux; caller already ensures Linux
    max_memory_bytes = config["max_memory_mb"] * 1024 * 1024
    try:
        resource.setrlimit(resource.RLIMIT_AS, (max_memory_bytes, max_memory_bytes))
        resource.setrlimit(resource.RLIMIT_DATA, (max_memory_bytes, max_memory_bytes))
        resource.setrlimit(resource.RLIMIT_STACK, (8 * 1024 * 1024, 8 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        if hasattr(resource, "RLIMIT_NPROC"):
            resource.setrlimit(resource.RLIMIT_NPROC, (0, 0))
        cpu_limit_fraction = max(0.1, min(config.get("max_cpu_percent", 100.0), 100.0) / 100.0)
        cpu_seconds = max(1, int(config["timeout_seconds"] * cpu_limit_fraction))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
    except Exception as exc:
        # The sandbox will still run, but we log the failure in the parent
        raise RuntimeError(f"Failed to set resource limits: {exc}") from exc


def _sandbox_process_worker(
    code: str,
    context: dict[str, Any],
    config: dict[str, Any],
    result_queue: multiprocessing.Queue,
):
    """Worker process that compiles and executes user code."""
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    start_time = datetime.now()
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024

    def _write_result(success: bool, return_value: Any, error: str | None):
        execution_time = (datetime.now() - start_time).total_seconds()
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_used = max(0, final_memory - initial_memory)
        result_queue.put(
            {
                "success": success,
                "stdout": stdout_capture.getvalue(),
                "stderr": stderr_capture.getvalue(),
                "return_value": return_value,
                "execution_time": execution_time,
                "memory_used_mb": memory_used,
                "error": error,
            }
        )

    try:
        _apply_resource_limits(config)

        byte_code = compile_restricted(code, filename="<sandbox>", mode="exec")
        if byte_code.errors:
            _write_result(False, None, f"Compilation errors: {byte_code.errors}")
            return

        safe_env = _build_execution_env(context, set(config["allowed_imports"]))

        with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
            exec(byte_code.code, safe_env)

        _write_result(True, safe_env.get("_", None), None)
    except Exception as exc:
        _write_result(False, None, str(exc))


@dataclass
class ExecutionResult:
    """Result of code execution"""
    success: bool
    stdout: str
    stderr: str
    return_value: Any
    execution_time: float
    memory_used_mb: float
    error: str | None = None


class SandboxConfig:
    """Configuration for sandbox execution"""

    def __init__(
        self,
        timeout_seconds: int = 30,
        max_memory_mb: int = 128,  # Conservative for NUC
        max_cpu_percent: float = 50.0,  # Don't hog NUC resources
        allowed_imports: set[str] | None = None,
    ):
        self.timeout_seconds = timeout_seconds
        self.max_memory_mb = max_memory_mb
        self.max_cpu_percent = max_cpu_percent
        self.allowed_imports = set(allowed_imports or {
            "json",
            "datetime",
            "math",
            "re",
            "typing",
            "collections",
            "itertools",
            "functools",
        })

    def as_payload(self) -> dict[str, Any]:
        """Serialize configuration for subprocess usage."""
        return {
            "timeout_seconds": self.timeout_seconds,
            "max_memory_mb": self.max_memory_mb,
            "allowed_imports": list(self.allowed_imports),
            "max_cpu_percent": self.max_cpu_percent,
        }


class PythonSandbox:
    """
    Secure Python code execution sandbox.

    Security layers:
    1. RestrictedPython - AST-level restrictions
    2. Resource limits - CPU, memory, time
    3. Import restrictions - Whitelist only
    4. Process isolation - Separate process (future)
    """

    def __init__(self, config: SandboxConfig = None):
        self.config = config or SandboxConfig()
        self._mp_context = multiprocessing.get_context("spawn")

    async def execute(self, code: str, context: dict[str, Any] = None) -> ExecutionResult:
        """
        Execute Python code in sandbox.

        Args:
            code: Python code to execute
            context: Variables available to code (e.g., MCP tool functions)

        Returns:
            ExecutionResult with output, errors, metrics
        """
        if sys.platform != "linux":
            raise RuntimeError("Sandbox execution is only supported on Linux hosts")

        sanitized_context = self._sanitize_context(context or {})

        try:
            result_payload = await asyncio.to_thread(
                self._run_in_subprocess,
                code,
                sanitized_context,
            )
        except Exception as exc:
            logger.error("Sandbox execution error: %s\n%s", exc, traceback.format_exc())
            return ExecutionResult(
                success=False,
                stdout="",
                stderr="",
                return_value=None,
                execution_time=0,
                memory_used_mb=0,
                error=str(exc),
            )

        return ExecutionResult(
            success=result_payload["success"],
            stdout=result_payload["stdout"],
            stderr=result_payload["stderr"],
            return_value=result_payload["return_value"],
            execution_time=result_payload["execution_time"],
            memory_used_mb=result_payload["memory_used_mb"],
            error=result_payload["error"],
        )

    def _sanitize_context(self, context: dict[str, Any]) -> dict[str, Any]:
        """Ensure user-provided context only contains JSON-serializable primitives."""

        def _sanitize(value: Any, depth: int = 0, size_tracker: list[int] = None) -> Any:
            """Recursively sanitize context values with size tracking."""
            if size_tracker is None:
                size_tracker = [0]
            
            if depth > MAX_CONTEXT_DEPTH:
                raise ValueError("Context nesting exceeds allowed depth")

            if isinstance(value, SAFE_VALUE_TYPES):
                # Estimate size (rough approximation)
                if isinstance(value, str):
                    size_tracker[0] += len(value.encode('utf-8'))
                else:
                    size_tracker[0] += 16  # Approximate size for numbers/bool/None
                return value

            if isinstance(value, (list, tuple)):
                sanitized_list = []
                for item in value:
                    if size_tracker[0] > MAX_CONTEXT_SIZE:
                        raise ValueError(f"Context size exceeds {MAX_CONTEXT_SIZE} bytes")
                    sanitized_list.append(_sanitize(item, depth + 1, size_tracker))
                return sanitized_list

            if isinstance(value, dict):
                sanitized_dict = {}
                for key, val in value.items():
                    if not isinstance(key, str):
                        raise ValueError("Context dictionary keys must be strings")
                    if size_tracker[0] > MAX_CONTEXT_SIZE:
                        raise ValueError(f"Context size exceeds {MAX_CONTEXT_SIZE} bytes")
                    # Add key size
                    size_tracker[0] += len(key.encode('utf-8'))
                    sanitized_dict[key] = _sanitize(val, depth + 1, size_tracker)
                return sanitized_dict

            raise ValueError("Only JSON-serializable context values are permitted")

        # Check initial context size (rough check)
        try:
            serialized_size = len(json.dumps(context, default=str))
            if serialized_size > MAX_CONTEXT_SIZE:
                raise ValueError(f"Context size ({serialized_size} bytes) exceeds limit ({MAX_CONTEXT_SIZE} bytes)")
        except (TypeError, ValueError) as e:
            # If we can't serialize, sanitization will catch it
            pass

        sanitized: dict[str, Any] = {}
        size_tracker = [0]
        for key, value in context.items():
            if key in {"__builtins__", "__name__", "__package__"}:
                raise ValueError(f"Context key '{key}' is reserved")
            if size_tracker[0] > MAX_CONTEXT_SIZE:
                raise ValueError(f"Context size exceeds {MAX_CONTEXT_SIZE} bytes")
            sanitized[key] = _sanitize(value, depth=0, size_tracker=size_tracker)

        return sanitized

    def _run_in_subprocess(self, code: str, context: dict[str, Any]) -> dict[str, Any]:
        """Execute user code inside an isolated subprocess."""
        result_queue: multiprocessing.Queue = self._mp_context.Queue(maxsize=1)
        config_payload = self.config.as_payload()

        process = self._mp_context.Process(
            target=_sandbox_process_worker,
            args=(code, context, config_payload, result_queue),
            daemon=True,
        )

        process.start()
        
        try:
            process.join(self.config.timeout_seconds + 1)

            if process.is_alive():
                logger.warning(f"Process {process.pid} exceeded timeout, terminating")
                process.terminate()
                process.join(timeout=5)
                
                # Force kill if still alive after terminate
                if process.is_alive():
                    logger.error(f"Process {process.pid} did not terminate, killing")
                    process.kill()
                    process.join(timeout=2)
                
                raise TimeoutError(f"Execution exceeded {self.config.timeout_seconds}s timeout")

            try:
                result_payload = result_queue.get_nowait()
            except queue.Empty as exc:
                raise RuntimeError("Sandbox process produced no output") from exc
        finally:
            # Ensure process is cleaned up even on exception
            if process.is_alive():
                logger.warning(f"Cleaning up orphaned process {process.pid}")
                try:
                    process.terminate()
                    process.join(timeout=2)
                    if process.is_alive():
                        process.kill()
                        process.join(timeout=1)
                except Exception as cleanup_exc:
                    logger.error(f"Error during process cleanup: {cleanup_exc}")
            
            # Clean up queue resources
            try:
                result_queue.close()
                result_queue.join_thread()
            except Exception as queue_exc:
                logger.warning(f"Error closing result queue: {queue_exc}")

        return result_payload
