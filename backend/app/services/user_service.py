"""User service: list users, assign/remove roles."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import InvalidRoleError, UserNotFoundError
from app.domain.models.user import User
from app.repositories.user_repo import RefreshTokenRepository, UserRepository

VALID_ROLES = {"student", "instructor", "super-admin"}


class UserService:
    """Business logic for user management operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.token_repo = RefreshTokenRepository(session)

    async def list_users(
        self, org_id: str, offset: int = 0, limit: int = 50
    ) -> tuple[list[User], int]:
        """
        List users in an organization with pagination.

        Args:
            org_id: Organization ID to filter by.
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            Tuple of (list of users, total count).

        """
        return await self.user_repo.list_users(org_id, offset, limit)

    async def assign_role(self, user_id: str, role: str) -> User:
        """
        Assign a role to a user.

        Only super-admin can assign roles (enforced at the route level).
        Revokes all refresh tokens for the user so that the next token
        refresh picks up the new role set.

        Args:
            user_id: The user's ID.
            role: The role to assign.

        Returns:
            Updated user object.

        Raises:
            UserNotFoundError: If user doesn't exist.
            InvalidRoleError: If the role is not valid.

        """
        if role not in VALID_ROLES:
            msg = f"Invalid role: {role}"
            raise InvalidRoleError(msg)

        user = await self.user_repo.find_by_id(user_id)
        if not user:
            msg = "User not found"
            raise UserNotFoundError(msg)

        user.add_role(role)
        await self.user_repo.save(user)

        # H2: Invalidate all sessions so the role change takes effect immediately.
        # The user must re-authenticate to get a new token with updated roles.
        await self.token_repo.revoke_all_for_user(user_id)

        return user

    async def remove_role(self, user_id: str, role: str) -> User:
        """
        Remove a role from a user.

        Only super-admin can remove roles (enforced at the route level).
        Revokes all refresh tokens for the user so that the next token
        refresh picks up the updated role set.

        Args:
            user_id: The user's ID.
            role: The role to remove.

        Returns:
            Updated user object.

        Raises:
            UserNotFoundError: If user doesn't exist.
            InvalidRoleError: If the role is not valid or the user doesn't have it.

        """
        if role not in VALID_ROLES:
            msg = f"Invalid role: {role}"
            raise InvalidRoleError(msg)

        user = await self.user_repo.find_by_id(user_id)
        if not user:
            msg = "User not found"
            raise UserNotFoundError(msg)

        if not user.has_role(role):
            msg = f"User does not have role: {role}"
            raise InvalidRoleError(msg)

        user.remove_role(role)
        await self.user_repo.save(user)

        # H2: Invalidate all sessions so the role removal takes effect immediately.
        # A demoted user (e.g. instructor → student) must re-authenticate
        # to get a token reflecting the reduced privileges.
        await self.token_repo.revoke_all_for_user(user_id)

        return user
