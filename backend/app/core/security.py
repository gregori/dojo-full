"""Core security utilities: JWT, password hashing, Google OAuth token verification."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Payload to encode in the token (must include 'sub', 'email', 'roles', 'org_id').
        expires_delta: Optional custom expiration time. Defaults to JWT_ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns:
        Encoded JWT string.

    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta
        or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(
        to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
    )


def create_refresh_token_raw() -> str:
    """
    Generate a raw refresh token string (URL-safe, cryptographically random).

    This token is stored as a SHA-256 hash in the database.
    The raw token is sent to the client only once.
    """
    return secrets.token_urlsafe(64)


def hash_token(token: str) -> str:
    """
    Hash a token using SHA-256 for secure storage.

    Args:
        token: The raw token string to hash.

    Returns:
        Hex-encoded SHA-256 hash of the token.

    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_token(token: str) -> dict:
    """
    Verify and decode a JWT access token.

    Args:
        token: The JWT string to verify.

    Returns:
        The decoded payload dict.

    Raises:
        TokenExpiredError: If the token has expired.
        AuthenticationError: If the token is invalid.

    """
    from app.core.exceptions import AuthenticationError, TokenExpiredError

    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") != "access":
            msg = "Invalid token type"
            raise AuthenticationError(msg)
        return payload
    except JWTError as e:
        error_str = str(e)
        if "expir" in error_str.lower():
            msg = "Token has expired"
            raise TokenExpiredError(msg)
        msg = "Invalid token"
        raise AuthenticationError(msg)


def verify_google_id_token(id_token_str: str) -> dict:
    """
    Verify a Google OAuth2 ID token.

    Args:
        id_token_str: The ID token string from Google.

    Returns:
        Dict with user info from the ID token (sub, email, name, etc.).

    Raises:
        AuthenticationError: If the token is invalid or audience doesn't match.

    """
    from app.core.exceptions import AuthenticationError

    try:
        return id_token.verify_oauth2_token(
            id_token_str,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except Exception as e:
        msg = f"Invalid Google ID token: {e!s}"
        raise AuthenticationError(msg)
