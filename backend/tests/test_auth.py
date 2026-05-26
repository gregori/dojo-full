"""Tests for auth API endpoints."""

import pytest
from httpx import AsyncClient


class TestRegister:
    """Test user registration endpoint."""

    @pytest.mark.asyncio
    async def test_register_success(
        self, async_client: AsyncClient, db_session, default_org
    ):
        """Test successful user registration."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@test.com",
                "password": "testpassword123",
                "name": "New User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "newuser@test.com"
        assert data["user"]["name"] == "New User"
        assert "student" in data["user"]["roles"]
        assert "access_token" in response.cookies

    @pytest.mark.asyncio
    async def test_register_duplicate_email(
        self, async_client: AsyncClient, db_session, test_user
    ):
        """Test registration with an email that already exists."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,
                "password": "testpassword123",
                "name": "Duplicate User",
            },
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_register_invalid_email(
        self, async_client: AsyncClient, db_session, default_org
    ):
        """Test registration with invalid email format."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "testpassword123",
                "name": "Bad Email",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_short_password(
        self, async_client: AsyncClient, db_session, default_org
    ):
        """Test registration with password shorter than 8 characters."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "shortpw@test.com",
                "password": "short",
                "name": "Short Password",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_short_name(
        self, async_client: AsyncClient, db_session, default_org
    ):
        """Test registration with name shorter than 2 characters."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "shortname@test.com",
                "password": "testpassword123",
                "name": "A",
            },
        )
        assert response.status_code == 422


class TestLogin:
    """Test user login endpoint."""

    @pytest.mark.asyncio
    async def test_login_success(
        self, async_client: AsyncClient, db_session, test_user
    ):
        """Test successful login with valid credentials."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": "student@test.com",
                "password": "testpassword123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == "student@test.com"
        assert "access_token" in response.cookies

    @pytest.mark.asyncio
    async def test_login_invalid_password(
        self, async_client: AsyncClient, db_session, test_user
    ):
        """Test login with incorrect password."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": "student@test.com",
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(
        self, async_client: AsyncClient, db_session, default_org
    ):
        """Test login with email that doesn't exist."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@test.com",
                "password": "testpassword123",
            },
        )
        assert response.status_code == 401


class TestLogout:
    """Test user logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_success(
        self, async_client: AsyncClient, db_session, test_user
    ):
        """Test successful logout clears cookies."""
        # First login
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "student@test.com", "password": "testpassword123"},
        )
        assert login_response.status_code == 200

        # Then logout
        response = await async_client.post("/api/v1/auth/logout")
        assert response.status_code == 204


class TestMe:
    """Test get current user endpoint."""

    @pytest.mark.asyncio
    async def test_me_authenticated(
        self, async_client: AsyncClient, db_session, test_user
    ):
        """Test getting current user profile with valid token."""
        # Login first
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "student@test.com", "password": "testpassword123"},
        )
        assert login_response.status_code == 200

        # Get profile
        response = await async_client.get("/api/v1/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "student@test.com"
        assert data["name"] == "Test Student"

    @pytest.mark.asyncio
    async def test_me_unauthenticated(
        self, async_client: AsyncClient, db_session, default_org
    ):
        """Test getting profile without authentication returns 401."""
        response = await async_client.get("/api/v1/auth/me")
        assert response.status_code == 401
