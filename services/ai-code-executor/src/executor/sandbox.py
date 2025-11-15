"""
Secure Python code execution sandbox for MCP code execution pattern.
NUC-optimized: Minimal resource overhead, single-process isolation.
"""

import sys
import io
import contextlib
import asyncio
import resource
import signal
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import traceback
from RestrictedPython import compile_restricted
import psutil
import logging

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of code execution"""
    success: bool
    stdout: str
    stderr: str
    return_value: Any
    execution_time: float
    memory_used_mb: float
    error: Optional[str] = None


class SandboxConfig:
    """Configuration for sandbox execution"""

    def __init__(
        self,
        timeout_seconds: int = 30,
        max_memory_mb: int = 128,  # Conservative for NUC
        max_cpu_percent: float = 50.0,  # Don't hog NUC resources
        allowed_imports: set = None
    ):
        self.timeout_seconds = timeout_seconds
        self.max_memory_mb = max_memory_mb
        self.max_cpu_percent = max_cpu_percent
        self.allowed_imports = allowed_imports or {
            'json', 'datetime', 'math', 're', 'typing',
            'collections', 'itertools', 'functools'
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

    async def execute(self, code: str, context: Dict[str, Any] = None) -> ExecutionResult:
        """
        Execute Python code in sandbox.

        Args:
            code: Python code to execute
            context: Variables available to code (e.g., MCP tool functions)

        Returns:
            ExecutionResult with output, errors, metrics
        """
        start_time = datetime.now()
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Capture stdout/stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        try:
            # Compile code with RestrictedPython
            byte_code = compile_restricted(
                code,
                filename='<sandbox>',
                mode='exec'
            )

            if byte_code.errors:
                return ExecutionResult(
                    success=False,
                    stdout="",
                    stderr="",
                    return_value=None,
                    execution_time=0,
                    memory_used_mb=0,
                    error=f"Compilation errors: {byte_code.errors}"
                )

            # Build safe execution environment
            safe_env = self._build_safe_environment(context or {})

            # Execute with timeout and resource limits
            with contextlib.redirect_stdout(stdout_capture), \
                 contextlib.redirect_stderr(stderr_capture):

                # Set resource limits (Linux only)
                self._set_resource_limits()

                # Execute code with timeout
                try:
                    result = await asyncio.wait_for(
                        self._execute_code(byte_code.code, safe_env),
                        timeout=self.config.timeout_seconds
                    )
                except asyncio.TimeoutError:
                    raise TimeoutError(
                        f"Execution exceeded {self.config.timeout_seconds}s timeout"
                    )

            # Calculate metrics
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            final_memory = process.memory_info().rss / 1024 / 1024
            memory_used = max(0, final_memory - initial_memory)

            return ExecutionResult(
                success=True,
                stdout=stdout_capture.getvalue(),
                stderr=stderr_capture.getvalue(),
                return_value=result,
                execution_time=execution_time,
                memory_used_mb=memory_used
            )

        except Exception as e:
            logger.error(f"Sandbox execution error: {e}\n{traceback.format_exc()}")

            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()

            return ExecutionResult(
                success=False,
                stdout=stdout_capture.getvalue(),
                stderr=stderr_capture.getvalue(),
                return_value=None,
                execution_time=execution_time,
                memory_used_mb=0,
                error=str(e)
            )

    def _build_safe_environment(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Build safe execution environment with restricted globals"""
        safe_env = {
            '__builtins__': {
                # Safe built-ins only
                'print': print,
                'len': len,
                'range': range,
                'str': str,
                'int': int,
                'float': float,
                'bool': bool,
                'list': list,
                'dict': dict,
                'set': set,
                'tuple': tuple,
                'min': min,
                'max': max,
                'sum': sum,
                'sorted': sorted,
                'enumerate': enumerate,
                'zip': zip,
                'map': map,
                'filter': filter,
                'any': any,
                'all': all,
                'isinstance': isinstance,
                'type': type,
                'abs': abs,
                'round': round,
                # NO: open, eval, exec, compile, __import__
            }
        }

        # Add context (MCP tool functions)
        safe_env.update(context)

        return safe_env

    def _set_resource_limits(self):
        """Set resource limits for execution (Linux only)"""
        if sys.platform != 'linux':
            logger.warning("Resource limits only supported on Linux")
            return

        try:
            # Memory limit (soft, hard)
            max_memory_bytes = self.config.max_memory_mb * 1024 * 1024
            resource.setrlimit(
                resource.RLIMIT_AS,
                (max_memory_bytes, max_memory_bytes)
            )

            # CPU time limit
            resource.setrlimit(
                resource.RLIMIT_CPU,
                (self.config.timeout_seconds, self.config.timeout_seconds)
            )
        except Exception as e:
            logger.warning(f"Failed to set resource limits: {e}")

    async def _execute_code(self, code, env: Dict[str, Any]) -> Any:
        """Execute compiled code in safe environment"""
        # Run in executor to avoid blocking event loop
        loop = asyncio.get_event_loop()

        def _run():
            exec(code, env)
            # Return the last expression result if available
            return env.get('_', None)

        return await loop.run_in_executor(None, _run)
