"""Tests for Intelligence Observatory Dashboard"""

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


class TestDashboard:
    async def test_dashboard_returns_html(self, client):
        resp = await client.get("/dashboard")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/html; charset=utf-8"

    async def test_dashboard_contains_chartjs(self, client):
        resp = await client.get("/dashboard")
        assert "chart.js" in resp.text.lower()

    async def test_dashboard_contains_timeline_section(self, client):
        resp = await client.get("/dashboard")
        assert "Timeline" in resp.text

    async def test_dashboard_contains_obsolescent_prompts_section(self, client):
        resp = await client.get("/dashboard")
        assert "Obsolescent" in resp.text or "Prompts" in resp.text

    async def test_dashboard_contains_signal_correlations_section(self, client):
        resp = await client.get("/dashboard")
        assert "Signal" in resp.text or "Correlation" in resp.text

    async def test_dashboard_contains_capability_changes_section(self, client):
        resp = await client.get("/dashboard")
        assert "Capability" in resp.text

    async def test_dashboard_contains_unused_memories_section(self, client):
        resp = await client.get("/dashboard")
        assert "Unused" in resp.text or "Memories" in resp.text

    async def test_dashboard_contains_script_block(self, client):
        resp = await client.get("/dashboard")
        assert "<script>" in resp.text

    async def test_dashboard_has_title(self, client):
        resp = await client.get("/dashboard")
        assert "<title>" in resp.text

    async def test_dashboard_returns_200_with_data(self, client):
        await client.post("/api/timeline", json={
            "date": "2024-06-01",
            "recipes": [{"evaluation": {"score": 0.9}, "memory_version": 1, "prompt_version": 1}],
        })
        await client.post("/api/prompts/obsolescent", json={
            "prompt_id": "p1", "prompt_name": "test", "usage_count": 5,
            "avg_relevance": 0.3, "trend": "declining",
        })
        await client.post("/api/signals/correlation", json={
            "signal_name": "s1", "correlation_coefficient": 0.75,
            "p_value": 0.01, "sample_size": 100,
        })

        resp = await client.get("/dashboard")
        assert resp.status_code == 200

    async def test_dashboard_contains_stats_bar(self, client):
        resp = await client.get("/dashboard")
        assert "stats-bar" in resp.text or "Stat" in resp.text

    async def test_dashboard_chart_containers(self, client):
        resp = await client.get("/dashboard")
        assert "timelineChart" in resp.text or "capabilityChart" in resp.text

    async def test_dashboard_fetch_endpoints(self, client):
        resp = await client.get("/dashboard")
        assert "observatory/stats" in resp.text
        assert "timeline/" in resp.text
        assert "prompts/obsolescent" in resp.text
        assert "signals/correlations" in resp.text
        assert "capability/changes" in resp.text
        assert "memories/unused" in resp.text

    async def test_dashboard_grid_layout(self, client):
        resp = await client.get("/dashboard")
        assert "grid" in resp.text
        assert "card" in resp.text

    async def test_dashboard_loading_state(self, client):
        resp = await client.get("/dashboard")
        assert "Loading" in resp.text or "loading" in resp.text

    async def test_dashboard_error_state(self, client):
        resp = await client.get("/dashboard")
        assert "error" in resp.text.lower() or "Error" in resp.text or "catch" in resp.text
