"""Unit tests for app.dependencies.auth module."""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from jose import jwt

from app.core.config import get_settings
from app.core.security import create_access_token, get_password_hash
from app.dependencies.auth import (
    get_current_admin,
    get_current_instructor_or_admin,
    get_current_user,
)
from app.models import User


class TestGetCurrentUser:
    """Tests for get_current_user dependency."""

    def test_valid_token_returns_user(self, db_session):
        """Should return user for valid JWT token."""
        user = User(
            email="auth@dojo.com",
            password_hash=get_password_hash("pass123"),
            full_name="Auth User",
            role="admin",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()

        token = create_access_token({"sub": user.id, "role": user.role})
        result = get_current_user(token=token, db=db_session)
        assert result.id == user.id
        assert result.email == "auth@dojo.com"

    def test_invalid_token_raises_401(self, db_session):
        """Should raise 401 for invalid JWT token."""
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token="invalid.token.here", db=db_session)
        assert exc_info.value.status_code == 401

    def test_expired_token_raises_401(self, db_session):
        """Should raise 401 for expired JWT token."""
        from datetime import timedelta

        token = create_access_token(
            {"sub": "some-user-id"},
            expires_delta=timedelta(seconds=-1),
        )
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=token, db=db_session)
        assert exc_info.value.status_code == 401

    def test_nonexistent_user_raises_401(self, db_session):
        """Should raise 401 for token with nonexistent user ID."""
        token = create_access_token({"sub": "nonexistent-id", "role": "admin"})
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=token, db=db_session)
        assert exc_info.value.status_code == 401

    def test_inactive_user_raises_403(self, db_session):
        """Should raise 403 for inactive user."""
        user = User(
            email="inactive@dojo.com",
            password_hash=get_password_hash("pass123"),
            full_name="Inactive User",
            role="admin",
            is_active=False,
        )
        db_session.add(user)
        db_session.commit()

        token = create_access_token({"sub": user.id, "role": user.role})
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=token, db=db_session)
        assert exc_info.value.status_code == 403

    def test_token_missing_sub_raises_401(self, db_session):
        """Should raise 401 for token without sub claim."""
        settings = get_settings()
        token = jwt.encode({"role": "admin"}, settings.secret_key, algorithm=settings.algorithm)
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=token, db=db_session)
        assert exc_info.value.status_code == 401


class TestGetCurrentAdmin:
    """Tests for get_current_admin dependency."""

    def test_admin_user_passes(self, db_session):
        """Should return user when role is admin."""
        user = User(
            email="admin@dojo.com",
            password_hash=get_password_hash("pass123"),
            full_name="Admin User",
            role="admin",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()

        result = get_current_admin(current_user=user)
        assert result.role == "admin"

    def test_instructor_user_raises_403(self, db_session):
        """Should raise 403 when role is instructor."""
        user = User(
            email="instructor@dojo.com",
            password_hash=get_password_hash("pass123"),
            full_name="Instructor User",
            role="instructor",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            get_current_admin(current_user=user)
        assert exc_info.value.status_code == 403


class TestGetCurrentInstructorOrAdmin:
    """Tests for get_current_instructor_or_admin dependency."""

    def test_instructor_passes(self, db_session):
        """Should return user when role is instructor."""
        user = User(
            email="instructor@dojo.com",
            password_hash=get_password_hash("pass123"),
            full_name="Instructor User",
            role="instructor",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()

        result = get_current_instructor_or_admin(current_user=user)
        assert result.role == "instructor"

    def test_admin_passes(self, db_session):
        """Should return user when role is admin."""
        user = User(
            email="admin2@dojo.com",
            password_hash=get_password_hash("pass123"),
            full_name="Admin User",
            role="admin",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()

        result = get_current_instructor_or_admin(current_user=user)
        assert result.role == "admin"

    def test_other_role_raises_403(self, db_session):
        """Should raise 403 for non-admin/instructor role."""
        # Create a mock user with a role that's not admin or instructor
        user = MagicMock(spec=User)
        user.role = "student"
        user.is_active = True

        with pytest.raises(HTTPException) as exc_info:
            get_current_instructor_or_admin(current_user=user)
        assert exc_info.value.status_code == 403
