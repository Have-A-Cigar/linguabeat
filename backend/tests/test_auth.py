"""Integration tests for /auth endpoints."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _register(client: AsyncClient, email: str = "user@test.dev", password: str = "pass1234"):
    return await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "language_level": "B1"},
    )


async def _login(client: AsyncClient, email: str = "user@test.dev", password: str = "pass1234"):
    return await client.post(
        "/api/v1/auth/login",
        content=f"username={email}&password={password}",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )


async def test_register_success(client: AsyncClient):
    r = await _register(client, email="new@test.dev")
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == "new@test.dev"
    assert data["language_level"] == "B1"
    assert data["is_active"] is True
    assert "id" in data


async def test_register_duplicate(client: AsyncClient):
    await _register(client, email="dup@test.dev")
    r = await _register(client, email="dup@test.dev")
    assert r.status_code == 400
    assert "already registered" in r.json()["detail"]


async def test_login_success(client: AsyncClient):
    await _register(client, email="login@test.dev")
    r = await _login(client, email="login@test.dev")
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(client: AsyncClient):
    await _register(client, email="wrongpw@test.dev")
    r = await _login(client, email="wrongpw@test.dev", password="badpass")
    assert r.status_code == 401


async def test_login_unknown_user(client: AsyncClient):
    r = await _login(client, email="nobody@test.dev")
    assert r.status_code == 401


async def test_me_authenticated(client: AsyncClient):
    await _register(client, email="me@test.dev")
    login_r = await _login(client, email="me@test.dev")
    token = login_r.json()["access_token"]

    r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == "me@test.dev"


async def test_me_unauthenticated(client: AsyncClient):
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401


async def test_me_invalid_token(client: AsyncClient):
    r = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer notavalidtoken"})
    assert r.status_code == 401


async def test_refresh_sets_new_token(client: AsyncClient):
    await _register(client, email="refresh@test.dev")
    login_r = await _login(client, email="refresh@test.dev")
    assert "refresh_token" in login_r.cookies

    r = await client.post("/api/v1/auth/refresh")
    assert r.status_code == 200
    assert "access_token" in r.json()


async def test_refresh_no_cookie(client: AsyncClient):
    # fresh client with no cookie → 401
    r = await client.post("/api/v1/auth/refresh", cookies={})
    assert r.status_code == 401


async def test_logout_clears_cookie(client: AsyncClient):
    await _register(client, email="logout@test.dev")
    await _login(client, email="logout@test.dev")

    r = await client.post("/api/v1/auth/logout")
    assert r.status_code == 200
    assert r.json() == {"ok": True}
