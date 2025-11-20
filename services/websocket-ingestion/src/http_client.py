import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

import aiohttp


class SimpleHTTPClient:
    """Simple HTTP client for sending events to enrichment service with circuit breaker"""

    def __init__(self, enrichment_url: str):
        self.enrichment_url = enrichment_url
        self.session = None

        # Circuit breaker state
        self.consecutive_failures = 0
        self.max_consecutive_failures = 5
        self.circuit_open = False
        self.circuit_open_until = None
        self.circuit_reset_timeout = 30  # seconds

        # Statistics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def send_event(self, event_data: dict[str, Any]) -> bool:
        """Send event to enrichment service with circuit breaker and retry logic"""
        self.total_requests += 1

        # Check circuit breaker state
        if self.circuit_open:
            # Check if it's time to reset
            if datetime.now() >= self.circuit_open_until:
                logging.info("Circuit breaker: Attempting to close circuit (half-open state)")
                self.circuit_open = False
                self.consecutive_failures = 0
            else:
                # Circuit is open - fail fast to prevent CPU overload
                remaining_seconds = (self.circuit_open_until - datetime.now()).total_seconds()
                logging.warning(f"Circuit breaker OPEN - skipping request (reopens in {remaining_seconds:.1f}s)")
                self.failed_requests += 1
                return False

        # Try to send with limited retries
        max_retries = 2  # Reduced from 3 to prevent CPU overload

        for attempt in range(max_retries):
            try:
                async with self.session.post(
                    f"{self.enrichment_url}/events",
                    json=event_data,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        # Success - reset circuit breaker
                        self.consecutive_failures = 0
                        self.successful_requests += 1
                        logging.debug(f"Event sent successfully on attempt {attempt + 1}")
                        return True
                    else:
                        logging.warning(f"HTTP {response.status} on attempt {attempt + 1}")

            except Exception as e:
                logging.warning(f"Attempt {attempt + 1} failed: {e}")

            # Backoff between retries (exponential)
            if attempt < max_retries - 1:
                await asyncio.sleep(1.0 * (2 ** attempt))  # 1s, 2s

        # All retries failed - increment failure counter
        self.consecutive_failures += 1
        self.failed_requests += 1

        # Open circuit if too many consecutive failures
        if self.consecutive_failures >= self.max_consecutive_failures:
            self.circuit_open = True
            self.circuit_open_until = datetime.now() + timedelta(seconds=self.circuit_reset_timeout)
            logging.error(f"Circuit breaker OPENED after {self.consecutive_failures} consecutive failures "
                         f"(will retry in {self.circuit_reset_timeout}s)")
        else:
            logging.error(f"Failed to send event after {max_retries} attempts "
                         f"({self.consecutive_failures}/{self.max_consecutive_failures} consecutive failures)")

        return False

    def get_stats(self) -> dict[str, Any]:
        """Get HTTP client statistics"""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": (self.successful_requests / self.total_requests * 100) if self.total_requests > 0 else 0,
            "circuit_breaker": {
                "is_open": self.circuit_open,
                "consecutive_failures": self.consecutive_failures,
                "reopens_at": self.circuit_open_until.isoformat() if self.circuit_open_until else None
            }
        }
