from __future__ import annotations

import time
import pytest
from polymarket_trades.infrastructure.api_client.rate_limiter import RateLimiter


class TestRateLimiter:
    async def test_allows_first_request_immediately(self) -> None:
        """First acquire should complete without any sleep delay."""
        limiter = RateLimiter(requests_per_second=10)
        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start
        # Should complete almost immediately (within 50ms)
        assert elapsed < 0.05

    async def test_delays_subsequent_request_when_rate_exceeded(self) -> None:
        """Second acquire within the interval should be delayed."""
        limiter = RateLimiter(requests_per_second=10)  # 100ms interval
        await limiter.acquire()
        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start
        # Should wait approximately 100ms
        assert elapsed >= 0.05  # At least 50ms delay
        assert elapsed < 0.3    # But not too long

    async def test_respects_different_rates(self) -> None:
        """Rate limiter with 2 rps should wait ~500ms between requests."""
        limiter = RateLimiter(requests_per_second=2)  # 500ms interval
        await limiter.acquire()
        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start
        # Should wait approximately 500ms
        assert elapsed >= 0.4   # At least 400ms
        assert elapsed < 0.8    # But not more than 800ms
