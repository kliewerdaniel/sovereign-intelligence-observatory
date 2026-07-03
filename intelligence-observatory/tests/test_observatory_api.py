"""Integration tests for Intelligence Observatory API"""

import pytest
from httpx import AsyncClient, ASGITransport

from src.database import ObservatoryDatabase
from src.api import app, get_db


@pytest.fixture
async def db():
    _db = ObservatoryDatabase(":memory:")
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


class TestObservatoryAPI:
    async def test_health(self, client):
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["service"] == "intelligence-observatory"

    async def test_update_timeline(self, client):
        resp = await client.post("/api/timeline", json={
            "date": "2024-06-01",
            "recipes": [
                {"evaluation": {"score": 0.9}, "memory_version": 5, "prompt_version": 3},
                {"evaluation": {"score": 0.7}, "memory_version": 5, "prompt_version": 3},
            ],
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "updated"

    async def test_get_timeline(self, client):
        await client.post("/api/timeline", json={
            "date": "2024-06-15",
            "recipes": [{"evaluation": {"score": 0.8}, "memory_version": 1, "prompt_version": 1}],
        })
        resp = await client.get("/api/timeline/2024-06-01/2024-06-30")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_obsolescent_prompts(self, client):
        resp = await client.post("/api/prompts/obsolescent", json={
            "prompt_id": "prompt-1",
            "prompt_name": "old_prompt",
            "usage_count": 5,
            "avg_relevance": 0.3,
            "trend": "declining",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "updated"

        get_resp = await client.get("/api/prompts/obsolescent")
        assert get_resp.status_code == 200

    async def test_unused_memories(self, client):
        resp = await client.post("/api/memories/unused", json={
            "memory_id": "mem-1",
            "title": "old_doc",
            "usage_count": 2,
            "last_retrieved": "2020-01-01",
        })
        assert resp.status_code == 200
        get_resp = await client.get("/api/memories/unused")
        assert get_resp.status_code == 200

    async def test_signal_correlations(self, client):
        resp = await client.post("/api/signals/correlation", json={
            "signal_name": "test_signal",
            "correlation_coefficient": 0.75,
            "p_value": 0.01,
            "sample_size": 100,
        })
        assert resp.status_code == 200
        get_resp = await client.get("/api/signals/correlations")
        assert get_resp.status_code == 200
        assert len(get_resp.json()) >= 1

    async def test_capability_changes(self, client):
        resp = await client.post("/api/capability/change", json={
            "task": "classification",
            "date_from": "2024-01-01",
            "date_to": "2024-06-01",
            "score_change": -0.15,
            "change_type": "regression",
            "factors": ["data_shift"],
            "severity": "medium",
        })
        assert resp.status_code == 200
        get_resp = await client.get("/api/capability/changes")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert "regressions" in data
        assert "improvements" in data

    async def test_observatory_stats(self, client):
        resp = await client.get("/api/observatory/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "timeline_entries" in data
        assert "last_updated" in data

    async def test_generate_report(self, client):
        resp = await client.get(
            "/api/observatory/report",
            params={"date_from": "2024-01-01", "date_to": "2024-12-31"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "report_title" in data
        assert "summary" in data
