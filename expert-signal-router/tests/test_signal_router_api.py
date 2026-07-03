"""Integration tests for Expert Signal Router API"""

import pytest
from unittest.mock import AsyncMock
from httpx import AsyncClient, ASGITransport

from src.database import SignalDatabase
from src.api import app, get_db


@pytest.fixture
async def db():
    _db = SignalDatabase(":memory:")
    yield _db
    await _db.close()


@pytest.fixture
async def client(db):
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


class TestSignalRouterAPI:
    async def test_health(self, client):
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["service"] == "expert-signal-router"

    async def test_route_auto_accepted(self, client):
        resp = await client.post(
            "/api/route/test-recipe-1",
            json={"recipe_id": "test-recipe-1", "objective": "test", "confidence": 0.99},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["signal_type"] == "auto_accepted"
        assert data["decision"] == "accepted"

    async def test_route_cheap(self, client):
        resp = await client.post(
            "/api/route/test-recipe-2",
            json={"recipe_id": "test-recipe-2", "objective": "test", "confidence": 0.85},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["signal_type"] == "cheap"
        assert data["decision"] == "accepted"

    async def test_route_expert_review(self, client):
        resp = await client.post(
            "/api/route/test-recipe-3",
            json={"recipe_id": "test-recipe-3", "objective": "test", "confidence": 0.60},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["signal_type"] == "expert"
        assert data["decision"] == "pending_review"

    async def test_pending_reviews(self, client):
        await client.post(
            "/api/route/test-recipe-4",
            json={"recipe_id": "test-recipe-4", "objective": "test", "confidence": 0.30},
        )
        resp = await client.get("/api/pending-reviews")
        assert resp.status_code == 200
        pending = resp.json()
        assert len(pending) >= 1
        assert all(r["decision"] == "pending_review" for r in pending)

    async def test_record_review(self, client):
        await client.post(
            "/api/route/test-recipe-5",
            json={"recipe_id": "test-recipe-5", "objective": "test", "confidence": 0.40},
        )
        pending = (await client.get("/api/pending-reviews")).json()
        if pending:
            eval_id = pending[0]["id"]
            resp = await client.post(
                f"/api/review/{eval_id}",
                json={"decision": "accepted", "feedback": "Looks good", "reviewed_by": "expert_1"},
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "review_recorded"

    async def test_signal_stats(self, client):
        resp = await client.get("/api/signals/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "by_signal" in data
