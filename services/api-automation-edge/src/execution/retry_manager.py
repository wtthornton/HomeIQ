"""
Retry Manager and Circuit Breaker

Epic E2: Retry with exponential backoff and circuit breaker
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker per HA instance.
    
    States:
    - CLOSED: Normal operation
    - OPEN: Failing, reject requests immediately
    - HALF_OPEN: Testing if service recovered
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        success_threshold: int = 2
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening
            timeout: Time to wait before half-open
            success_threshold: Successes needed to close from half-open
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.success_threshold = success_threshold
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.opened_at: Optional[float] = None
    
    def record_success(self):
        """Record successful request"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self._close()
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0
    
    def record_failure(self):
        """Record failed request"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self._open()
        elif self.state == CircuitState.HALF_OPEN:
            self._open()
    
    def _open(self):
        """Open circuit breaker"""
        self.state = CircuitState.OPEN
        self.opened_at = time.time()
        self.success_count = 0
        logger.warning(
            f"Circuit breaker opened (failures: {self.failure_count})"
        )
    
    def _close(self):
        """Close circuit breaker"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.opened_at = None
        logger.info("Circuit breaker closed")
    
    def _half_open(self):
        """Move to half-open state"""
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        logger.info("Circuit breaker half-open (testing)")
    
    def is_open(self) -> bool:
        """Check if circuit is open"""
        if self.state == CircuitState.OPEN:
            # Check if timeout has passed
            if self.opened_at and (time.time() - self.opened_at) >= self.timeout:
                self._half_open()
                return False
            return True
        return False
    
    def allow_request(self) -> bool:
        """Check if request should be allowed"""
        if self.is_open():
            return False
        return True


class RetryManager:
    """
    Retry manager with exponential backoff.
    
    Features:
    - Exponential backoff for transient errors
    - Classify transient vs permanent errors
    - Mark automation invalid on permanent incompatibility
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        multiplier: float = 2.0
    ):
        """
        Initialize retry manager.
        
        Args:
            max_retries: Maximum retry attempts
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            multiplier: Exponential backoff multiplier
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
    
    def is_transient_error(self, error: Exception) -> bool:
        """
        Classify error as transient or permanent.
        
        Args:
            error: Exception to classify
        
        Returns:
            True if transient (should retry)
        """
        error_str = str(error).lower()
        
        # Transient errors (network, timeout, temporary)
        transient_patterns = [
            "timeout",
            "connection",
            "network",
            "temporary",
            "503",
            "502",
            "504",
            "429",  # Rate limit
        ]
        
        # Permanent errors (not found, invalid, auth)
        permanent_patterns = [
            "404",  # Not found
            "401",  # Unauthorized
            "403",  # Forbidden
            "400",  # Bad request (usually permanent)
            "invalid",
            "not found",
            "does not exist",
        ]
        
        # Check for permanent first
        for pattern in permanent_patterns:
            if pattern in error_str:
                return False
        
        # Check for transient
        for pattern in transient_patterns:
            if pattern in error_str:
                return True
        
        # Default: assume transient for unknown errors
        return True
    
    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with retry logic.
        
        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
        
        Returns:
            Function result
        
        Raises:
            Exception: If all retries fail
        """
        delay = self.initial_delay
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                last_error = e
                
                # Check if error is permanent
                if not self.is_transient_error(e):
                    logger.error(f"Permanent error (no retry): {e}")
                    raise
                
                # Check if we've exhausted retries
                if attempt >= self.max_retries:
                    logger.error(f"Max retries exceeded: {e}")
                    raise
                
                # Wait before retry
                logger.warning(
                    f"Retry {attempt + 1}/{self.max_retries} after {delay:.2f}s: {e}"
                )
                await asyncio.sleep(delay)
                
                # Exponential backoff
                delay = min(delay * self.multiplier, self.max_delay)
        
        # Should not reach here, but just in case
        if last_error:
            raise last_error
