"""Unit tests for app.core.rate_limiter module."""
import pytest
from app.core.rate_limiter import RateLimiter


class TestRateLimiter:
    """Tests for the RateLimiter class."""

    def test_initial_state_allows_requests(self):
        """New rate limiter should allow requests."""
        limiter = RateLimiter()
        assert limiter.is_allowed("user1") is True

    def test_record_and_check_attempts(self):
        """After recording attempts, is_allowed should reflect count."""
        limiter = RateLimiter()
        limiter.max_attempts = 3
        limiter.window_seconds = 60

        assert limiter.is_allowed("user1") is True
        limiter.record_attempt("user1")
        limiter.record_attempt("user1")
        limiter.record_attempt("user1")

        assert limiter.is_allowed("user1") is False

    def test_different_identifiers_independent(self):
        """Different identifiers should have independent rate limits."""
        limiter = RateLimiter()
        limiter.max_attempts = 2

        limiter.record_attempt("user1")
        limiter.record_attempt("user1")

        assert limiter.is_allowed("user1") is False
        assert limiter.is_allowed("user2") is True

    def test_check_rate_limit_raises_on_exceeded(self):
        """check_rate_limit should raise HTTPException when limit exceeded."""
        from fastapi import HTTPException
        limiter = RateLimiter()
        limiter.max_attempts = 1

        limiter.check_rate_limit("user1")  # First attempt OK

        with pytest.raises(HTTPException) as exc_info:
            limiter.check_rate_limit("user1")
        assert exc_info.value.status_code == 429

    def test_check_rate_limit_records_attempt(self):
        """check_rate_limit should record the attempt when allowed."""
        limiter = RateLimiter()
        limiter.max_attempts = 2

        limiter.check_rate_limit("user1")
        # After 1 attempt, should still allow 1 more
        assert limiter.is_allowed("user1") is True

        limiter.check_rate_limit("user1")
        # After 2 attempts, should be blocked
        assert limiter.is_allowed("user1") is False

    def test_clean_old_attempts(self):
        """Old attempts outside the window should be cleaned."""
        from datetime import datetime, timedelta
        limiter = RateLimiter()
        limiter.max_attempts = 2
        limiter.window_seconds = 60

        # Manually insert an old attempt
        limiter._attempts["user1"] = [datetime.utcnow() - timedelta(seconds=120)]

        # Old attempt should be cleaned, so new request is allowed
        assert limiter.is_allowed("user1") is True

    def test_get_key_returns_identifier(self):
        """_get_key should return the identifier unchanged."""
        limiter = RateLimiter()
        assert limiter._get_key("test_id") == "test_id"