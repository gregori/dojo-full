"""
Authentication and authorization dependencies for FastAPI.

Uses cookie-based authentication (NOT OAuth2PasswordBearer).
Tokens are extracted from httpOnly cookies set by the backend.
"""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.get_db import get_db
from app.core.exceptions import AuthenticationError, TokenExpiredError
from app.core.security import verify_token
from app.domain.models.user import User
from app.repositories.user_repo import UserRepository

# OAuth2 scheme for OpenAPI documentation only — NOT used for actual token extraction.
# This allows Swagger UI to show a "Authorize" button and document the auth flow.
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login", auto_error=False
)


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Extract and verify the current user from the access_token cookie.

    This is the primary authentication dependency. It reads the JWT access token
    from the httpOnly cookie (NOT from the Authorization header).

    Args:
        request: The incoming HTTP request (used to read cookies).
        db: Database session from dependency injection.

    Returns:
        The authenticated User object.

    Raises:
        HTTPException 401: If no token, token is invalid, or user not found.

    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        payload = verify_token(token)
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user_repo = UserRepository(db)
    user = await user_repo.find_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


def require_role(*roles: str):
    """
    Factory that returns a dependency checking if the current user has one of the required roles.

    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(user: User = Depends(require_role("super-admin"))):
            ...

    Args:
        *roles: One or more role strings. The user must have at least one.

    Returns:
        A FastAPI dependency function.

    """

    async def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if not any(current_user.has_role(role) for role in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return role_checker
