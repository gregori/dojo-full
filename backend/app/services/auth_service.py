"""Authentication service: register, login, OAuth, refresh, logout."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import AuthenticationError, TokenExpiredError
from app.core.security import (
    create_access_token,
    create_refresh_token_raw,
    hash_password,
    hash_token,
    verify_google_id_token,
    verify_password,
)
from app.domain.exceptions import DuplicateEmailError
from app.domain.models.user import RefreshToken, User
from app.repositories.user_repo import RefreshTokenRepository, UserRepository


class AuthService:
    """Business logic for authentication operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.token_repo = RefreshTokenRepository(session)

    async def register(
        self, email: str, password: str, name: str, org_id: str
    ) -> tuple[str, str, User]:
        """
        Register a new user with email/password.

        Args:
            email: User's email address.
            password: Plain text password (will be hashed).
            name: User's display name.
            org_id: Organization ID to assign the user to.

        Returns:
            Tuple of (access_token, refresh_token, user).

        Raises:
            DuplicateEmailError: If email is already registered.

        """
        # Check for existing user
        existing = await self.user_repo.find_by_email(email)
        if existing:
            msg = "Email already registered"
            raise DuplicateEmailError(msg)

        # Create user
        user = User(
            id=str(uuid.uuid4()),
            org_id=org_id,
            email=email,
            password_hash=hash_password(password),
            name=name,
            roles=["student"],
            auth_provider="email",
        )
        user = await self.user_repo.create(user)

        # Create tokens
        access_token, refresh_token = await self._create_tokens(user)

        return access_token, refresh_token, user

    async def login(self, email: str, password: str) -> tuple[str, str, User]:
        """
        Authenticate a user with email/password.

        Args:
            email: User's email address.
            password: Plain text password.

        Returns:
            Tuple of (access_token, refresh_token, user).

        Raises:
            AuthenticationError: If credentials are invalid.

        """
        user = await self.user_repo.find_by_email(email)
        if not user:
            msg = "Invalid email or password"
            raise AuthenticationError(msg)

        # Check that user has a password (not Google-only)
        if user.password_hash is None:
            msg = "Invalid email or password"
            raise AuthenticationError(msg)

        if not verify_password(password, user.password_hash):
            msg = "Invalid email or password"
            raise AuthenticationError(msg)

        # Create tokens
        access_token, refresh_token = await self._create_tokens(user)

        return access_token, refresh_token, user

    async def google_oauth_login(
        self, code: str, state: str, expected_state: str
    ) -> tuple[str, str, User]:
        """
        Process Google OAuth login.

        Args:
            code: Authorization code from Google.
            state: CSRF state parameter from the callback.
            expected_state: Expected CSRF state from the cookie.

        Returns:
            Tuple of (access_token, refresh_token, user).

        Raises:
            AuthenticationError: If state doesn't match or token is invalid.

        """
        # Validate CSRF state
        if state != expected_state:
            msg = "CSRF state mismatch"
            raise AuthenticationError(msg)

        # Exchange code for tokens using httpx
        import httpx

        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )
            if token_response.status_code != 200:
                msg = "Failed to exchange authorization code"
                raise AuthenticationError(msg)

            token_data = token_response.json()
            id_token_str = token_data.get("id_token")
            if not id_token_str:
                msg = "No ID token in Google response"
                raise AuthenticationError(msg)

        # Verify the ID token
        idinfo = verify_google_id_token(id_token_str)
        google_sub = idinfo.get("sub")
        email = idinfo.get("email")
        name = idinfo.get("name", email.split("@")[0])

        if not google_sub or not email:
            msg = "Missing required fields in Google ID token"
            raise AuthenticationError(msg)

        # Find or create user
        user = await self.user_repo.find_by_google_sub(google_sub)
        if user:
            # Existing Google user - log them in
            pass
        else:
            # Check if email matches an existing user (account linking)
            user = await self.user_repo.find_by_email(email)
            if user:
                # Link Google account to existing email user
                user.google_sub = google_sub
                user.auth_provider = "google"
                await self.user_repo.save(user)
            else:
                # Create new user via Google
                default_org_id = "00000000-0000-0000-0000-000000000001"
                user = User(
                    id=str(uuid.uuid4()),
                    org_id=default_org_id,
                    email=email,
                    password_hash=None,
                    name=name,
                    roles=["student"],
                    auth_provider="google",
                    google_sub=google_sub,
                )
                user = await self.user_repo.create(user)

        # Create tokens
        access_token, refresh_token = await self._create_tokens(user)

        return access_token, refresh_token, user

    async def refresh_access_token(
        self, raw_refresh_token: str
    ) -> tuple[str, str]:
        """
        Rotate a refresh token and issue new access + refresh tokens.

        Uses optimistic locking on updated_at to detect concurrent refresh attempts.

        Args:
            raw_refresh_token: The raw refresh token from the client's cookie.

        Returns:
            Tuple of (new_access_token, new_refresh_token).

        Raises:
            AuthenticationError: If the token is invalid, expired, or already used.

        """
        token_hash = hash_token(raw_refresh_token)
        refresh_token = await self.token_repo.find_by_hash_with_updated_at(
            token_hash
        )

        if not refresh_token:
            msg = "Invalid refresh token"
            raise AuthenticationError(msg)

        if refresh_token.revoked:
            msg = "Refresh token has been revoked"
            raise AuthenticationError(msg)

        if refresh_token.expires_at < datetime.now(UTC):
            msg = "Refresh token has expired"
            raise TokenExpiredError(msg)

        # Revoke the old token with optimistic locking on updated_at
        original_updated_at = refresh_token.updated_at
        revoked = await self.token_repo.revoke(token_hash, original_updated_at)
        if not revoked:
            msg = "Refresh token already used"
            raise AuthenticationError(msg)

        # Get the user
        user = await self.user_repo.find_by_id(refresh_token.user_id)
        if not user:
            msg = "User not found"
            raise AuthenticationError(msg)

        # Create new tokens
        access_token, new_refresh_token = await self._create_tokens(user)

        # Opportunistic cleanup of expired/revoked tokens
        await self.token_repo.cleanup_expired()

        return access_token, new_refresh_token

    async def logout(self, raw_refresh_token: str) -> None:
        """
        Revoke a refresh token (logout).

        Args:
            raw_refresh_token: The raw refresh token from the client's cookie.

        """
        if not raw_refresh_token:
            return

        token_hash = hash_token(raw_refresh_token)
        refresh_token = await self.token_repo.find_by_hash_with_updated_at(
            token_hash
        )
        if not refresh_token:
            # Token not found or already revoked — logout is still successful
            return

        # Revoke with optimistic locking; if it fails (already revoked), that's fine for logout
        await self.token_repo.revoke(token_hash, refresh_token.updated_at)

    async def _create_tokens(self, user: User) -> tuple[str, str]:
        """
        Create access and refresh tokens for a user.

        Args:
            user: The user to create tokens for.

        Returns:
            Tuple of (access_token, raw_refresh_token).

        """
        # Create access token
        token_data = {
            "sub": user.id,
            "email": user.email,
            "roles": user.roles,
            "org_id": user.org_id,
        }
        access_token = create_access_token(token_data)

        # Create refresh token
        raw_refresh_token = create_refresh_token_raw()
        token_hash = hash_token(raw_refresh_token)
        expires_at = datetime.now(UTC) + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )

        refresh_token = RefreshToken(
            id=str(uuid.uuid4()),
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        await self.token_repo.create(refresh_token)

        return access_token, raw_refresh_token
