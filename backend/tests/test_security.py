"""Tests for security core functions."""

from datetime import timedelta

import pytest

from app.config import settings
from app.core.exceptions import AuthenticationError, TokenExpiredError
from app.core.security import (
    create_access_token,
    create_refresh_token_raw,
    hash_password,
    hash_token,
    verify_password,
    verify_token,
)


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password(self):
        """Test that password hashing produces a bcrypt hash."""
        hashed = hash_password("testpassword123")
        assert hashed is not None
        assert hashed != "testpassword123"
        assert hashed.startswith("$2b$")

    def test_verify_password_correct(self):
        """Test that correct password verifies successfully."""
        hashed = hash_password("testpassword123")
        assert verify_password("testpassword123", hashed) is True

    def test_verify_password_incorrect(self):
        """Test that incorrect password fails verification."""
        hashed = hash_password("testpassword123")
        assert verify_password("wrongpassword", hashed) is False

    def test_hash_password_different_hashes(self):
        """Test that hashing the same password produces different hashes (bcrypt salt)."""
        hashed1 = hash_password("testpassword123")
        hashed2 = hash_password("testpassword123")
        assert hashed1 != hashed2  # Different salts


class TestJWT:
    """Test JWT token creation and verification."""

    def test_create_access_token(self):
        """Test that access token is created with correct payload."""
        data = {
            "sub": "user-123",
            "email": "test@test.com",
            "roles": ["student"],
            "org_id": "org-1",
        }
        token = create_access_token(data)
        assert token is not None
        assert isinstance(token, str)

    def test_verify_valid_token(self):
        """Test that a valid token can be verified."""
        data = {
            "sub": "user-123",
            "email": "test@test.com",
            "roles": ["student"],
            "org_id": "org-1",
        }
        token = create_access_token(data)
        payload = verify_token(token)
        assert payload["sub"] == "user-123"
        assert payload["email"] == "test@test.com"
        assert payload["roles"] == ["student"]
        assert payload["org_id"] == "org-1"
        assert payload["type"] == "access"

    def test_verify_expired_token(self):
        """Test that an expired token raises TokenExpiredError."""
        data = {
            "sub": "user-123",
            "email": "test@test.com",
            "roles": ["student"],
            "org_id": "org-1",
        }
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))
        with pytest.raises(TokenExpiredError):
            verify_token(token)

    def test_verify_invalid_token(self):
        """Test that an invalid token raises AuthenticationError."""
        with pytest.raises(AuthenticationError):
            verify_token("invalid.token.here")

    def test_verify_token_wrong_type(self):
        """Test that a token without 'access' type raises AuthenticationError."""
        from jose import jwt

        data = {"sub": "user-123", "type": "refresh"}
        token = jwt.encode(
            data, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
        )
        with pytest.raises(AuthenticationError, match="Invalid token type"):
            verify_token(token)


class TestRefreshToken:
    """Test refresh token generation and hashing."""

    def test_create_refresh_token_raw(self):
        """Test that raw refresh token is generated."""
        token = create_refresh_token_raw()
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # Should be a long random string

    def test_create_refresh_token_unique(self):
        """Test that each refresh token is unique."""
        token1 = create_refresh_token_raw()
        token2 = create_refresh_token_raw()
        assert token1 != token2

    def test_hash_token(self):
        """Test that token hashing produces SHA-256 hex digest."""
        token = create_refresh_token_raw()
        hashed = hash_token(token)
        assert hashed is not None
        assert isinstance(hashed, str)
        assert len(hashed) == 64  # SHA-256 hex digest length

    def test_hash_token_deterministic(self):
        """Test that hashing the same token produces the same hash."""
        token = "test-token-value"
        hash1 = hash_token(token)
        hash2 = hash_token(token)
        assert hash1 == hash2
