import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestRegister:
    async def test_register_success(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "newuser@example.com",
            "password": "StrongPass1",
            "full_name": "New User",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "newuser@example.com"
        assert "hashed_password" not in data  # never expose this

    async def test_register_duplicate_email(self, client: AsyncClient):
        payload = {"email": "dup@example.com", "password": "StrongPass1", "full_name": "Dup"}
        await client.post("/api/v1/auth/register", json=payload)
        resp = await client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 409

    async def test_register_weak_password(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "weak@example.com",
            "password": "short",
            "full_name": "Weak",
        })
        assert resp.status_code == 422

    async def test_register_no_uppercase(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "noupper@example.com",
            "password": "alllowercase1",
            "full_name": "No Upper",
        })
        assert resp.status_code == 422

    async def test_register_invalid_email(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "password": "StrongPass1",
            "full_name": "Bad Email",
        })
        assert resp.status_code == 422


class TestLogin:
    async def test_login_success(self, client: AsyncClient):
        await client.post("/api/v1/auth/register", json={
            "email": "loginuser@example.com",
            "password": "StrongPass1",
            "full_name": "Login User",
        })
        resp = await client.post("/api/v1/auth/login", json={
            "email": "loginuser@example.com",
            "password": "StrongPass1",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient):
        await client.post("/api/v1/auth/register", json={
            "email": "wrongpw@example.com",
            "password": "StrongPass1",
            "full_name": "Wrong PW",
        })
        resp = await client.post("/api/v1/auth/login", json={
            "email": "wrongpw@example.com",
            "password": "WrongPassword1",
        })
        assert resp.status_code == 401

    async def test_login_nonexistent_user(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "ghost@example.com",
            "password": "StrongPass1",
        })
        assert resp.status_code == 401

    async def test_protected_route_without_token(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/organizations",
            json={"org_name": "No Auth"}
        )
        assert resp.status_code == 403

    async def test_protected_route_invalid_token(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/organizations",
            json={"org_name": "Bad Token"},
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert resp.status_code == 401