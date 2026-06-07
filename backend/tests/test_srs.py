"""Integration tests for /srs endpoints."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _auth_header(client: AsyncClient, email: str) -> dict:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "pass1234", "language_level": "A1"},
    )
    r = await client.post(
        "/api/v1/auth/login",
        content=f"username={email}&password=pass1234",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_due_empty_for_new_user(client: AsyncClient):
    headers = await _auth_header(client, "srs_due@test.dev")
    r = await client.get("/api/v1/srs/due", headers=headers)
    assert r.status_code == 200
    assert r.json() == []


async def test_due_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/srs/due")
    assert r.status_code == 401


async def test_stats_zeros_for_new_user(client: AsyncClient):
    headers = await _auth_header(client, "srs_stats@test.dev")
    r = await client.get("/api/v1/srs/stats", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data == {"due_today": 0, "total": 0, "new_learning": 0, "in_review": 0}


async def test_stats_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/srs/stats")
    assert r.status_code == 401


async def test_review_nonexistent_word(client: AsyncClient):
    headers = await _auth_header(client, "srs_review@test.dev")
    r = await client.post(
        "/api/v1/srs/review",
        json={"user_word_id": "nonexistent-id", "quality": 4},
        headers=headers,
    )
    assert r.status_code == 400
