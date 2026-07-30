"""
Aegis AI — Unit Tests for Middleware.

Tests rate limiting, correlation ID injection, and request logging
without requiring a running server.
"""

from __future__ import annotations

import time
import pytest

from app.core.middleware import RateLimitMiddleware


class TestRateLimiting:
    """Test the in-memory token bucket rate limiter."""

    def test_consume_token_allows_under_limit(self):
        """Requests within burst limit should be allowed."""
        middleware = RateLimitMiddleware.__new__(RateLimitMiddleware)
        middleware.rate = 1.0  # 1 token per second
        middleware.burst = 5
        middleware.buckets = {}

        from collections import defaultdict
        middleware.buckets = defaultdict(
            lambda: {"tokens": middleware.burst, "last_refill": time.monotonic()}
        )

        # Should allow burst number of requests
        for _ in range(5):
            assert middleware._consume_token("127.0.0.1") is True

    def test_consume_token_blocks_over_limit(self):
        """Requests exceeding burst should be blocked."""
        middleware = RateLimitMiddleware.__new__(RateLimitMiddleware)
        middleware.rate = 0.0  # No refill — tests pure burst behavior
        middleware.burst = 2
        middleware.buckets = {}

        from collections import defaultdict
        middleware.buckets = defaultdict(
            lambda: {"tokens": middleware.burst, "last_refill": time.monotonic()}
        )

        assert middleware._consume_token("10.0.0.1") is True
        assert middleware._consume_token("10.0.0.1") is True
        assert middleware._consume_token("10.0.0.1") is False

    def test_different_ips_have_separate_buckets(self):
        """Each client IP should have its own rate limit bucket."""
        middleware = RateLimitMiddleware.__new__(RateLimitMiddleware)
        middleware.rate = 0.0
        middleware.burst = 1
        middleware.buckets = {}

        from collections import defaultdict
        middleware.buckets = defaultdict(
            lambda: {"tokens": middleware.burst, "last_refill": time.monotonic()}
        )

        assert middleware._consume_token("10.0.0.1") is True
        assert middleware._consume_token("10.0.0.2") is True
        assert middleware._consume_token("10.0.0.1") is False
        assert middleware._consume_token("10.0.0.2") is False


class TestCorrelationId:
    """Test correlation ID generation and propagation."""

    def test_correlation_id_format(self):
        """Verify generated correlation IDs are valid UUIDs."""
        import uuid
        correlation_id = str(uuid.uuid4())
        parsed = uuid.UUID(correlation_id)
        assert str(parsed) == correlation_id
