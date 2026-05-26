"""Tests for user API endpoints."""

import pytest
from httpx import AsyncClient


class TestListUsers:
    """Test list users endpoint."""

    @pytest.mark.asyncio
    async def test_list_users_as_instructor(
        self, async_client: AsyncClient, db_session, instructor_user, test_user
    ):
        """Test that instructor can list users."""
        # Login as instructor
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": "instructor@test.com",
                "password": "testpassword123",
            },
        )
        assert login_response.status_code == 200

        response = await async_client.get("/api/v1/users")
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_list_users_as_student_forbidden(
        self, async_client: AsyncClient, db_session, test_user
    ):
        """Test that student cannot list users (403)."""
        # Login as student
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "student@test.com", "password": "testpassword123"},
        )
        assert login_response.status_code == 200

        response = await async_client.get("/api/v1/users")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_list_users_pagination(
        self, async_client: AsyncClient, db_session, admin_user
    ):
        """Test list users with pagination parameters."""
        # Login as admin
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.com", "password": "testpassword123"},
        )
        assert login_response.status_code == 200

        response = await async_client.get("/api/v1/users?offset=0&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert data["offset"] == 0
        assert data["limit"] == 10


class TestAssignRole:
    """Test assign role endpoint."""

    @pytest.mark.asyncio
    async def test_assign_instructor_role(
        self, async_client: AsyncClient, db_session, admin_user, test_user
    ):
        """Test that super-admin can assign instructor role."""
        # Login as admin
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.com", "password": "testpassword123"},
        )
        assert login_response.status_code == 200

        response = await async_client.post(
            f"/api/v1/users/{test_user.id}/roles",
            json={"role": "instructor"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "instructor" in data["roles"]

    @pytest.mark.asyncio
    async def test_assign_role_as_instructor_forbidden(
        self, async_client: AsyncClient, db_session, instructor_user, test_user
    ):
        """Test that instructor cannot assign roles (403)."""
        # Login as instructor
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": "instructor@test.com",
                "password": "testpassword123",
            },
        )
        assert login_response.status_code == 200

        response = await async_client.post(
            f"/api/v1/users/{test_user.id}/roles",
            json={"role": "instructor"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_assign_invalid_role(
        self, async_client: AsyncClient, db_session, admin_user, test_user
    ):
        """Test assigning an invalid role returns 422."""
        # Login as admin
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.com", "password": "testpassword123"},
        )
        assert login_response.status_code == 200

        response = await async_client.post(
            f"/api/v1/users/{test_user.id}/roles",
            json={"role": "invalid-role"},
        )
        assert response.status_code == 422


class TestRemoveRole:
    """Test remove role endpoint."""

    @pytest.mark.asyncio
    async def test_remove_instructor_role(
        self,
        async_client: AsyncClient,
        db_session,
        admin_user,
        instructor_user,
    ):
        """Test that super-admin can remove instructor role."""
        # Login as admin
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.com", "password": "testpassword123"},
        )
        assert login_response.status_code == 200

        response = await async_client.delete(
            f"/api/v1/users/{instructor_user.id}/roles/instructor"
        )
        assert response.status_code == 200
        data = response.json()
        assert "instructor" not in data["roles"]

    @pytest.mark.asyncio
    async def test_remove_role_user_doesnt_have(
        self, async_client: AsyncClient, db_session, admin_user, test_user
    ):
        """Test removing a role the user doesn't have returns 400."""
        # Login as admin
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.com", "password": "testpassword123"},
        )
        assert login_response.status_code == 200

        response = await async_client.delete(
            f"/api/v1/users/{test_user.id}/roles/instructor"
        )
        assert response.status_code == 400
