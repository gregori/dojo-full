"""Unit tests for app.core.security module."""
import pytest
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.config import get_settings


class TestPasswordHashing:
    """Tests for password hashing and verification."""

    def test_hash_password_returns_string(self):
        """get_password_hash should return a bcrypt hash string."""
        result = get_password_hash("test123")
        assert isinstance(result, str)
        assert result.startswith("$2")

    def test_hash_password_different_each_time(self):
        """Each hash call should produce a different salt/hash."""
        h1 = get_password_hash("same_password")
        h2 = get_password_hash("same_password")
        assert h1 != h2  # different salts

    def test_verify_correct_password(self):
        """verify_password should return True for correct password."""
        hashed = get_password_hash("my_password")
        assert verify_password("my_password", hashed) is True

    def test_verify_wrong_password(self):
        """verify_password should return False for wrong password."""
        hashed = get_password_hash("my_password")
        assert verify_password("wrong_password", hashed) is False

    def test_verify_password_empty_string(self):
        """verify_password should handle empty string password."""
        hashed = get_password_hash("")
        assert verify_password("", hashed) is True

    def test_verify_password_long_password_truncated(self):
        """bcrypt truncates passwords at 72 bytes; verify should still work."""
        long_pw = "a" * 100
        hashed = get_password_hash(long_pw)
        # First 72 chars should match
        assert verify_password(long_pw, hashed) is True
        # Different password beyond 72 bytes won't matter
        assert verify_password("a" * 72 + "different", hashed) is True

    def test_verify_password_special_characters(self):
        """verify_password should handle special characters."""
        pw = "p@$$w0rd!#%^&*()"
        hashed = get_password_hash(pw)
        assert verify_password(pw, hashed) is True

    def test_verify_password_unicode(self):
        """verify_password should handle unicode characters."""
        pw = "senhação日本語"
        hashed = get_password_hash(pw)
        assert verify_password(pw, hashed) is True


class TestAccessToken:
    """Tests for JWT access token creation."""

    def test_create_token_returns_string(self):
        """create_access_token should return a JWT string."""
        token = create_access_token({"sub": "user123", "role": "admin"})
        assert isinstance(token, str)
        assert len(token) > 20

    def test_create_token_decodable(self):
        """Token should be decodable with the secret key."""
        from jose import jwt
        settings = get_settings()
        token = create_access_token({"sub": "user123", "role": "admin"})
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        assert payload["sub"] == "user123"
        assert payload["role"] == "admin"
        assert "exp" in payload

    def test_create_token_with_custom_expiry(self):
        """Token with custom expiry delta should be decodable."""
        from datetime import timedelta
        from jose import jwt
        settings = get_settings()
        token = create_access_token(
            {"sub": "user456"},
            expires_delta=timedelta(hours=1),
        )
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        assert payload["sub"] == "user456"

    def test_create_token_preserves_data(self):
        """Token should preserve all data fields."""
        from jose import jwt
        settings = get_settings()
        data = {"sub": "abc", "role": "instructor", "org_id": "org1"}
        token = create_access_token(data)
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        assert payload["sub"] == "abc"
        assert payload["role"] == "instructor"
        assert payload["org_id"] == "org1"