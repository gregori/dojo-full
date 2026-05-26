"""Middleware configuration: rate limiting with SlowAPI."""

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

# Rate limiter instance using client IP as the key
limiter = Limiter(key_func=get_remote_address)


def rate_limit_exceeded_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """
    Custom handler for rate limit exceeded responses.

    Returns a JSON response with a 429 status code and a user-friendly message.
    """
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Try again later."},
    )
