"""Integration tests for Sovereign Apprenticeship Engine API"""

import pytest
from httpx import AsyncClient, ASGITransport

from src.database import ApprenticeshipDatabase
from src.api import app, get_db


@pytest.fixture
async def db():
    _db = ApprenticeshipDatabase(":memory:")
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


class TestApprenticeshipAPI:
    async def test_health(self, client):
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["service"] == "sovereign-apprenticeship-engine"

    async def test_get_agent_state_creates_new(self, client):
        resp = await client.get("/api/agent/test-agent-1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_id"] == "test-agent-1"
        assert data["level"] == "fully_supervised"
        assert data["supervision_ratio"] == 1.0

    async def test_record_action(self, client):
        await client.get("/api/agent/action-agent")
        resp = await client.post(
            "/api/action/action-agent",
            json={"monitored": True, "quality_score": 0.9},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["action_recorded"] is True

    async def test_record_unmonitored_low_quality_increases_debt(self, client):
        await client.get("/api/agent/debt-agent")
        await client.post(
            "/api/action/debt-agent",
            json={"monitored": False, "quality_score": 0.5},
        )
        resp = await client.get("/api/agent/debt-agent")
        assert resp.json()["autonomy_debt"] > 0

    async def test_promote_agent(self, client):
        agent_id = "promote-agent"
        await client.get(f"/api/agent/{agent_id}")

        resp = await client.post(
            f"/api/promote/{agent_id}",
            json={
                "new_level": "approve_dangerous",
                "reason": "Testing promotion",
                "quality_threshold": 0.8,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["promoted"] is True
        assert data["to_level"] == "approve_dangerous"
        assert data["new_budget"] > 0

    async def test_promote_invalid_level(self, client):
        resp = await client.post(
            "/api/promote/invalid-agent",
            json={
                "new_level": "invalid",
                "reason": "test",
                "quality_threshold": 0.5,
            },
        )
        assert resp.status_code == 400

    async def test_get_transitions(self, client):
        agent_id = "transition-agent"
        await client.get(f"/api/agent/{agent_id}")
        await client.post(
            f"/api/promote/{agent_id}",
            json={
                "new_level": "approve_dangerous",
                "reason": "Testing transitions",
                "quality_threshold": 0.8,
            },
        )
        resp = await client.get(f"/api/transitions/{agent_id}")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_get_budget(self, client):
        resp = await client.get("/api/budget/budget-agent")
        assert resp.status_code == 200
        data = resp.json()
        assert "agent_id" in data
        assert "remaining" in data
