"""Unit tests for app.services.auth_service module."""

import pytest
from fastapi import HTTPException

from app.core.security import get_password_hash
from app.schemas import UserCreate, UserUpdate
from app.services.auth_service import AuthService, UserService
from tests.unit.conftest import make_user


class TestAuthServiceAuthenticate:
    """Tests for AuthService.authenticate_user."""

    def test_authenticate_valid_user(self, db_session):
        """Should return user when email and password are correct."""
        user = make_user(db_session, email="login@dojo.com", password_hash=get_password_hash("pass123"))
        db_session.commit()

        result = AuthService.authenticate_user(db_session, "login@dojo.com", "pass123")
        assert result is not None
        assert result.id == user.id

    def test_authenticate_wrong_password(self, db_session):
        """Should return None when password is wrong."""
        make_user(db_session, email="login@dojo.com", password_hash=get_password_hash("pass123"))
        db_session.commit()

        result = AuthService.authenticate_user(db_session, "login@dojo.com", "wrong_pass")
        assert result is None

    def test_authenticate_nonexistent_user(self, db_session):
        """Should return None when user doesn't exist."""
        result = AuthService.authenticate_user(db_session, "nobody@dojo.com", "pass123")
        assert result is None

    def test_authenticate_inactive_user(self, db_session):
        """Should return None when user is inactive."""
        make_user(db_session, email="inactive@dojo.com", password_hash=get_password_hash("pass123"), is_active=False)
        db_session.commit()

        result = AuthService.authenticate_user(db_session, "inactive@dojo.com", "pass123")
        assert result is None


class TestAuthServiceCreateToken:
    """Tests for AuthService.create_access_token."""

    def test_create_token_for_user(self, db_session):
        """Should create a valid JWT token for a user."""
        from jose import jwt

        from app.core.config import get_settings

        user = make_user(db_session, role="admin")
        db_session.commit()

        token = AuthService.create_access_token(user)
        settings = get_settings()
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        assert payload["sub"] == user.id
        assert payload["role"] == "admin"


class TestUserServiceCreate:
    """Tests for UserService.create_user."""

    def test_create_user_success(self, db_session):
        """Should create a new user with hashed password."""
        user_data = UserCreate(
            email="new@dojo.com",
            password="secret123",
            full_name="New User",
            role="instructor",
            is_active=True,
        )
        user = UserService.create_user(db_session, user_data)
        assert user.id is not None
        assert user.email == "new@dojo.com"
        assert user.full_name == "New User"
        assert user.role == "instructor"
        assert user.is_active is True
        # Password should be hashed, not stored in plain text
        assert user.password_hash != "secret123"
        assert user.password_hash.startswith("$2")

    def test_create_user_duplicate_email(self, db_session):
        """Should raise 409 when email already exists."""
        make_user(db_session, email="dup@dojo.com")
        db_session.commit()

        user_data = UserCreate(
            email="dup@dojo.com",
            password="pass",
            full_name="Dup User",
            role="instructor",
            is_active=True,
        )
        with pytest.raises(HTTPException) as exc_info:
            UserService.create_user(db_session, user_data)
        assert exc_info.value.status_code == 409


class TestUserServiceGet:
    """Tests for UserService.get_user and get_user_by_email."""

    def test_get_user_by_id(self, db_session):
        """Should return user by ID."""
        user = make_user(db_session)
        db_session.commit()

        found = UserService.get_user(db_session, user.id)
        assert found is not None
        assert found.id == user.id

    def test_get_user_not_found(self, db_session):
        """Should return None for nonexistent ID."""
        found = UserService.get_user(db_session, "nonexistent-id")
        assert found is None

    def test_get_user_by_email(self, db_session):
        """Should return user by email."""
        user = make_user(db_session, email="find@dojo.com")
        db_session.commit()

        found = UserService.get_user_by_email(db_session, "find@dojo.com")
        assert found is not None
        assert found.email == "find@dojo.com"

    def test_get_users_list(self, db_session):
        """Should return list of users."""
        make_user(db_session, email="u1@dojo.com")
        make_user(db_session, email="u2@dojo.com")
        db_session.commit()

        users = UserService.get_users(db_session)
        assert len(users) >= 2


class TestUserServiceUpdate:
    """Tests for UserService.update_user."""

    def test_update_user_name(self, db_session):
        """Should update user's full_name."""
        user = make_user(db_session, full_name="Old Name")
        db_session.commit()

        update = UserUpdate(full_name="New Name")
        updated = UserService.update_user(db_session, user.id, update)
        assert updated.full_name == "New Name"

    def test_update_user_password_hashes(self, db_session):
        """Should hash password when updating."""
        user = make_user(db_session, password_hash=get_password_hash("old_pass"))
        db_session.commit()

        update = UserUpdate(password="new_pass")
        updated = UserService.update_user(db_session, user.id, update)
        assert updated.password_hash != "new_pass"
        assert updated.password_hash != get_password_hash("old_pass")

    def test_update_user_email_conflict(self, db_session):
        """Should raise 409 when updating email to one that exists."""
        user1 = make_user(db_session, email="user1@dojo.com")
        user2 = make_user(db_session, email="user2@dojo.com")
        db_session.commit()

        update = UserUpdate(email="user2@dojo.com")
        with pytest.raises(HTTPException) as exc_info:
            UserService.update_user(db_session, user1.id, update)
        assert exc_info.value.status_code == 409

    def test_update_nonexistent_user(self, db_session):
        """Should raise 404 for nonexistent user."""
        update = UserUpdate(full_name="Ghost")
        with pytest.raises(HTTPException) as exc_info:
            UserService.update_user(db_session, "nonexistent", update)
        assert exc_info.value.status_code == 404


class TestUserServiceDelete:
    """Tests for UserService.delete_user (soft delete)."""

    def test_delete_user_sets_inactive(self, db_session):
        """Should set is_active to False instead of deleting."""
        user = make_user(db_session, is_active=True)
        db_session.commit()

        UserService.delete_user(db_session, user.id)
        db_session.commit()

        # Refresh from DB
        db_session.expire(user)
        assert user.is_active is False

    def test_delete_nonexistent_user(self, db_session):
        """Should raise 404 for nonexistent user."""
        with pytest.raises(HTTPException) as exc_info:
            UserService.delete_user(db_session, "nonexistent")
        assert exc_info.value.status_code == 404
