"""Custom exception classes for the application."""


class AuthenticationError(Exception):
    """Raised when authentication fails (invalid credentials, invalid token, etc.)."""


class AuthorizationError(Exception):
    """Raised when a user lacks sufficient permissions."""


class TokenExpiredError(Exception):
    """Raised when a JWT token has expired."""
