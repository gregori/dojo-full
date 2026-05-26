"""Auth routes: register, login, Google OAuth, refresh, logout, me."""

import secrets
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.get_current_user import get_current_user
from app.api.dependencies.get_db import get_db
from app.config import settings
from app.core.exceptions import AuthenticationError, TokenExpiredError
from app.core.middleware import limiter
from app.core.security import verify_token
from app.domain.exceptions import DuplicateEmailError
from app.domain.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
)
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

# Cookie settings
ACCESS_TOKEN_MAX_AGE = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60  # seconds
REFRESH_TOKEN_MAX_AGE = (
    settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
)  # seconds
COOKIE_SECURE = settings.is_production
COOKIE_SAMESITE = "lax"


def _set_auth_cookies(
    response: Response, access_token: str, refresh_token: str
) -> None:
    """Set httpOnly cookies for access and refresh tokens."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=ACCESS_TOKEN_MAX_AGE,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=REFRESH_TOKEN_MAX_AGE,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    """Clear auth cookies by setting Max-Age to 0."""
    response.set_cookie(
        key="access_token",
        value="",
        max_age=0,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value="",
        max_age=0,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/",
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
async def register(
    request: Request,
    response: Response,
    body: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Register a new user with email/password."""
    auth_service = AuthService(db)
    default_org_id = "00000000-0000-0000-0000-000000000001"

    try:
        access_token, refresh_token, user = await auth_service.register(
            email=body.email,
            password=body.password,
            name=body.name,
            org_id=default_org_id,
        )
    except DuplicateEmailError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    _set_auth_cookies(response, access_token, refresh_token)
    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=AuthResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Login with email/password."""
    auth_service = AuthService(db)

    try:
        access_token, refresh_token, user = await auth_service.login(
            email=body.email,
            password=body.password,
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    _set_auth_cookies(response, access_token, refresh_token)
    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.get("/google")
async def google_login(request: Request, response: Response):
    """
    Initiate Google OAuth flow.

    Generates a CSRF state token, stores it in a cookie, and redirects to Google.
    """
    # Generate CSRF state
    state = secrets.token_urlsafe(32)

    # Build Google OAuth URL
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={settings.GOOGLE_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=email+profile"
        f"&state={state}"
    )

    # Set state in httpOnly cookie for CSRF protection
    response.set_cookie(
        key="oauth_state",
        value=state,
        max_age=600,  # 10 minutes
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/",
    )

    # Redirect to Google
    from fastapi.responses import RedirectResponse

    return RedirectResponse(
        url=google_auth_url, status_code=status.HTTP_302_FOUND
    )


@router.get("/google/callback")
async def google_callback(
    request: Request,
    response: Response,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Google OAuth callback.

    Validates CSRF state, exchanges code for tokens, finds/creates user,
    sets auth cookies, and redirects to frontend.
    """
    # Check for OAuth error (user denied consent)
    if error:
        from fastapi.responses import RedirectResponse

        frontend_url = (
            settings.allowed_origins_list[0]
            if settings.allowed_origins_list
            else "http://localhost:5173"
        )
        error_response = RedirectResponse(
            url=f"{frontend_url}/auth/callback?success=false&error={error}",
            status_code=status.HTTP_302_FOUND,
        )
        # Clear OAuth state cookie on error
        error_response.set_cookie(
            key="oauth_state",
            value="",
            max_age=0,
            httponly=True,
            secure=COOKIE_SECURE,
            samesite=COOKIE_SAMESITE,
            path="/",
        )
        return error_response

    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing code or state parameter",
        )

    # Validate CSRF state
    expected_state = request.cookies.get("oauth_state")
    if not expected_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing OAuth state cookie",
        )

    auth_service = AuthService(db)

    try:
        (
            access_token,
            refresh_token,
            _user,
        ) = await auth_service.google_oauth_login(
            code=code,
            state=state,
            expected_state=expected_state,
        )
    except AuthenticationError as e:
        from fastapi.responses import RedirectResponse

        frontend_url = (
            settings.allowed_origins_list[0]
            if settings.allowed_origins_list
            else "http://localhost:5173"
        )
        error_response = RedirectResponse(
            url=f"{frontend_url}/auth/callback?success=false&error={e!s}",
            status_code=status.HTTP_302_FOUND,
        )
        # Clear OAuth state cookie on error
        error_response.set_cookie(
            key="oauth_state",
            value="",
            max_age=0,
            httponly=True,
            secure=COOKIE_SECURE,
            samesite=COOKIE_SAMESITE,
            path="/",
        )
        return error_response

    # Set auth cookies
    _set_auth_cookies(response, access_token, refresh_token)

    # Clear OAuth state cookie
    response.set_cookie(
        key="oauth_state",
        value="",
        max_age=0,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/",
    )

    # Redirect to frontend
    from fastapi.responses import RedirectResponse

    frontend_url = (
        settings.allowed_origins_list[0]
        if settings.allowed_origins_list
        else "http://localhost:5173"
    )
    return RedirectResponse(
        url=f"{frontend_url}/auth/callback?success=true",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/refresh", response_model=AuthResponse)
async def refresh(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Refresh access token using refresh token from cookie."""
    raw_refresh_token = request.cookies.get("refresh_token")
    if not raw_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
        )

    auth_service = AuthService(db)

    try:
        (
            access_token,
            new_refresh_token,
        ) = await auth_service.refresh_access_token(raw_refresh_token)
    except (AuthenticationError, TokenExpiredError) as e:
        _clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    # Get user from the new access token to build response
    payload = verify_token(access_token)
    user_repo = UserRepository(db)
    user = await user_repo.find_by_id(payload["sub"])

    _set_auth_cookies(response, access_token, new_refresh_token)
    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Logout: revoke refresh token and clear cookies."""
    raw_refresh_token = request.cookies.get("refresh_token")

    auth_service = AuthService(db)
    await auth_service.logout(raw_refresh_token)

    _clear_auth_cookies(response)


@router.get("/me", response_model=UserResponse)
async def me(current_user: Annotated[User, Depends(get_current_user)]):
    """Get current user profile."""
    return UserResponse.model_validate(current_user)
