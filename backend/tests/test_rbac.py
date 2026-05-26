"""Tests for role-based access control (RBAC)."""

import pytest
from httpx import AsyncClient


class TestRBAC:
    """Test role-based access control at the endpoint level."""

    @pytest.mark.asyncio
    async def test_no_token_returns_401(
        self, async_client: AsyncClient, db_session, default_org
    ):
        """Test that requests without token return 401."""
        response = await async_client.get("/api/v1/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(
        self, async_client: AsyncClient, db_session, default_org
    ):
        """Test that requests with invalid token return 401."""
        async_client.cookies.set(
            "access_token", "invalid.token.here", domain="test"
        )
        response = await async_client.get("/api/v1/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_student_cannot_access_instructor_endpoint(
        self, async_client: AsyncClient, db_session, test_user
    ):
        """Test that student role cannot access instructor-only endpoints."""
        # Login as student
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "student@test.com", "password": "testpassword123"},
        )
        assert login_response.status_code == 200

        # Try to access users list (instructor+ only)
        response = await async_client.get("/api/v1/users")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_instructor_can_access_instructor_endpoint(
        self, async_client: AsyncClient, db_session, instructor_user
    ):
        """Test that instructor role can access instructor+ endpoints."""
        # Login as instructor
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": "instructor@test.com",
                "password": "testpassword123",
            },
        )
        assert login_response.status_code == 200

        # Access users list
        response = await async_client.get("/api/v1/users")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_instructor_cannot_assign_roles(
        self, async_client: AsyncClient, db_session, instructor_user, test_user
    ):
        """Test that instructor cannot assign roles (super-admin only)."""
        # Login as instructor
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": "instructor@test.com",
                "password": "testpassword123",
            },
        )
        assert login_response.status_code == 200

        # Try to assign role
        response = await async_client.post(
            f"/api/v1/users/{test_user.id}/roles",
            json={"role": "instructor"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_can_assign_roles(
        self, async_client: AsyncClient, db_session, admin_user, test_user
    ):
        """Test that super-admin can assign roles."""
        # Login as admin
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.com", "password": "testpassword123"},
        )
        assert login_response.status_code == 200

        # Assign role
        response = await async_client.post(
            f"/api/v1/users/{test_user.id}/roles",
            json={"role": "instructor"},
        )
        assert response.status_code == 200
