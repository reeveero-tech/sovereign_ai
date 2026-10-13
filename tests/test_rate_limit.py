"""Regression tests for the /chat rate limiter."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import pytest
from rate_limit import SlidingWindowRateLimiter


def test_limiter_blocks_over_limit_and_returns_retry_after():
    limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=60)
    assert limiter.check("client-a", now=0) is None
    assert limiter.check("client-a", now=1) is None
    assert limiter.check("client-a", now=2) == 58


def test_limiter_expires_old_requests_at_window_boundary():
    limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=10)
    assert limiter.check("client-a", now=0) is None
    assert limiter.check("client-a", now=1) is None
    assert limiter.check("client-a", now=2) == 8
    assert limiter.check("client-a", now=10) is None


def test_limiter_keeps_clients_independent():
    limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=60)
    assert limiter.check("client-a", now=1) is None
    assert limiter.check("client-a", now=2) == 59
    assert limiter.check("client-b", now=2) is None


def test_limiter_bounds_number_of_tracked_clients():
    limiter = SlidingWindowRateLimiter(max_requests=1, max_clients=2)
    for index in range(10):
        assert limiter.check(f"client-{index}", now=float(index)) is None
    assert len(limiter._requests) <= 2


def test_chat_route_registers_rate_limit_dependency():
    from app import app, enforce_chat_rate_limit

    chat_route = next(route for route in app.routes if getattr(route, "path", None) == "/chat")
    assert any(
        dependency.call is enforce_chat_rate_limit
        for dependency in chat_route.dependant.dependencies
    )
    assert 429 in chat_route.responses


def test_limiter_rejects_invalid_limits():
    with pytest.raises(ValueError):
        SlidingWindowRateLimiter(max_requests=0)
