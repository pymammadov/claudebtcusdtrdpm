"""
Stage 4e: Monitor & Health Checks
Monitor system health and reconnection logic.
"""

import asyncio
import logging
from typing import Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class HealthMonitor:
    """Monitor system health and manage reconnections."""

    def __init__(
        self,
        max_retries: int = 5,
        initial_backoff_sec: float = 2.0,
        max_backoff_sec: float = 32.0,
    ):
        """
        Initialize monitor.

        Args:
            max_retries: Max reconnection attempts
            initial_backoff_sec: Initial backoff duration
            max_backoff_sec: Max backoff duration
        """
        self.max_retries = max_retries
        self.initial_backoff_sec = initial_backoff_sec
        self.max_backoff_sec = max_backoff_sec

        self.is_healthy = True
        self.last_heartbeat = datetime.utcnow()
        self.retry_count = 0
        self.current_backoff = initial_backoff_sec

    async def check_health(
        self,
        data_feed_connected: bool,
        executor_connected: bool,
    ) -> bool:
        """
        Check system health.

        Returns:
            True if healthy, False if needs reconnection
        """
        if not data_feed_connected or not executor_connected:
            self.is_healthy = False
            logger.warning("System unhealthy: connection lost")
            return False

        # Check heartbeat
        time_since_heartbeat = (datetime.utcnow() - self.last_heartbeat).total_seconds()
        if time_since_heartbeat > 60:  # 60 second timeout
            self.is_healthy = False
            logger.warning(f"No heartbeat for {time_since_heartbeat:.0f}s")
            return False

        self.is_healthy = True
        return True

    async def heartbeat(self):
        """Update heartbeat."""
        self.last_heartbeat = datetime.utcnow()

    async def exponential_backoff_retry(self):
        """Wait with exponential backoff, increment retry count."""
        if self.retry_count >= self.max_retries:
            logger.error(f"Max retries ({self.max_retries}) exhausted")
            raise RuntimeError("Reconnection failed: max retries exceeded")

        self.retry_count += 1
        backoff = min(self.current_backoff, self.max_backoff_sec)

        logger.info(f"Retry {self.retry_count}/{self.max_retries}, backoff {backoff}s")

        await asyncio.sleep(backoff)

        self.current_backoff *= 2

    def reset_retry(self):
        """Reset retry count and backoff on successful connection."""
        self.retry_count = 0
        self.current_backoff = self.initial_backoff_sec
        logger.info("Connection restored")

    def get_status(self) -> dict:
        """Get monitor status."""
        time_since_heartbeat = (datetime.utcnow() - self.last_heartbeat).total_seconds()

        return {
            "healthy": self.is_healthy,
            "retry_count": self.retry_count,
            "current_backoff_sec": self.current_backoff,
            "time_since_heartbeat_sec": time_since_heartbeat,
        }


class APIFailureHandler:
    """Handle API failures gracefully."""

    def __init__(self):
        """Initialize handler."""
        self.failed_requests = 0
        self.last_error = None
        self.last_error_time = None

    def record_failure(self, error: str):
        """Record an API failure."""
        self.failed_requests += 1
        self.last_error = error
        self.last_error_time = datetime.utcnow()

        logger.warning(f"API failure recorded: {error} (total: {self.failed_requests})")

    def should_halt(self) -> bool:
        """Determine if should halt trading due to API issues."""
        if self.failed_requests > 10:
            return True

        return False

    def reset(self):
        """Reset failure counter."""
        self.failed_requests = 0
        self.last_error = None
