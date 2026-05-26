"""User and refresh token repository for data access operations."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.user import RefreshToken, User


class UserRepository:
    """Repository for User CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user: User) -> User:
        """Create a new user in the database."""
        self.session.add(user)
        await self.session.flush()
        return user

    async def find_by_email(self, email: str) -> User | None:
        """Find a user by email address."""
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def find_by_google_sub(self, google_sub: str) -> User | None:
        """Find a user by Google subject ID."""
        result = await self.session.execute(
            select(User).where(User.google_sub == google_sub)
        )
        return result.scalar_one_or_none()

    async def find_by_id(self, user_id: str) -> User | None:
        """Find a user by ID."""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_users(
        self, org_id: str, offset: int = 0, limit: int = 50
    ) -> tuple[list[User], int]:
        """
        List users in an organization with pagination.

        Returns:
            Tuple of (list of users, total count).

        """
        count_result = await self.session.execute(
            select(func.count()).select_from(User).where(User.org_id == org_id)
        )
        total = count_result.scalar() or 0

        result = await self.session.execute(
            select(User)
            .where(User.org_id == org_id)
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        users = list(result.scalars().all())
        return users, total

    async def save(self, user: User) -> User:
        """Save (update) an existing user."""
        await self.session.flush()
        return user


class RefreshTokenRepository:
    """Repository for RefreshToken CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, refresh_token: RefreshToken) -> RefreshToken:
        """Create a new refresh token record."""
        self.session.add(refresh_token)
        await self.session.flush()
        return refresh_token

    async def find_by_hash(self, token_hash: str) -> RefreshToken | None:
        """Find a refresh token by its SHA-256 hash."""
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def find_by_hash_with_updated_at(
        self, token_hash: str
    ) -> RefreshToken | None:
        """
        Find a refresh token by hash, including updated_at for concurrent refresh detection.

        This method returns the token with its current updated_at value,
        which can be compared later to detect concurrent refresh attempts.
        """
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def revoke(
        self, token_hash: str, original_updated_at: datetime
    ) -> bool:
        """
        Revoke a refresh token by its hash with optimistic locking on updated_at.

        Uses optimistic locking to detect concurrent refresh attempts.
        If the updated_at value has changed since the token was read,
        another request has already used this token, and the revoke will fail.

        Args:
            token_hash: SHA-256 hash of the refresh token.
            original_updated_at: The updated_at value when the token was read.

        Returns:
            True if the token was successfully revoked, False if it was already used
            or updated by another concurrent request.

        """
        result = await self.session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.updated_at == original_updated_at,
                RefreshToken.revoked == False,  # noqa: E712
            )
            .values(revoked=True)
        )
        return result.rowcount > 0

    async def revoke_all_for_user(self, user_id: str) -> int:
        """
        Revoke all refresh tokens for a user.

        Returns:
            Number of tokens revoked.

        """
        result = await self.session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id, RefreshToken.revoked == False
            )
            .values(revoked=True)
        )
        return result.rowcount

    async def cleanup_expired(self) -> int:
        """
        Delete expired and revoked refresh tokens older than 30 days.

        Called opportunistically on each refresh token creation.

        Returns:
            Number of tokens deleted.

        """
        cutoff = datetime.now(UTC) - timedelta(days=30)
        # Delete tokens that are revoked OR expired more than 30 days ago
        from sqlalchemy import delete

        result = await self.session.execute(
            delete(RefreshToken).where(
                (RefreshToken.revoked == True)
                | (RefreshToken.expires_at < cutoff)
            )
        )
        return result.rowcount
