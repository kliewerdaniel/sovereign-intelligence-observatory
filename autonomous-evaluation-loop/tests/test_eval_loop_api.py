"""Integration tests for Autonomous Evaluation Loop API"""

import pytest
from httpx import AsyncClient, ASGITransport

from src.database import EvaluationDatabase
from src.api import app, get_db


@pytest.fixture
async def db():
    _db = EvaluationDatabase(":memory:")
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


class TestEvaluationLoopAPI:
    async def test_health(self, client):
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["service"] == "autonomous-evaluation-loop"

    async def test_create_signal(self, client):
        resp = await client.post("/api/signals", json={
            "signal_id": "test-signal-1",
            "name": "accuracy",
            "signal_type": "heuristic",
            "threshold": 0.8,
        })
        assert resp.status_code == 201
        assert resp.json()["status"] == "created"

    async def test_create_signal_rejects_invalid_type(self, client):
        resp = await client.post("/api/signals", json={
            "signal_id": "bad-signal",
            "name": "bad",
            "signal_type": "invalid",
            "threshold": 0.5,
        })
        assert resp.status_code == 422

    async def test_evaluate_recipe(self, client):
        await client.post("/api/signals", json={
            "signal_id": "eval-signal",
            "name": "evaluation",
            "signal_type": "structured",
            "threshold": 0.7,
        })
        resp = await client.post("/api/evaluate/test-recipe", json={
            "signal_id": "eval-signal",
            "score": 0.85,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["passed"] is True
        assert data["recipe_id"] == "test-recipe"

    async def test_evaluate_fails_with_bad_signal(self, client):
        resp = await client.post("/api/evaluate/test-recipe", json={
            "signal_id": "nonexistent",
            "score": 0.5,
        })
        assert resp.status_code == 404

    async def test_list_signals(self, client):
        resp = await client.get("/api/signals")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_drift_detection(self, client):
        await client.post("/api/signals", json={
            "signal_id": "drift-signal",
            "name": "drift_test",
            "signal_type": "heuristic",
            "threshold": 0.5,
        })
        await client.post("/api/evaluate/test-recipe-drift", json={
            "signal_id": "drift-signal",
            "score": 0.85,
        })
        resp = await client.get("/api/signals/drift/drift-signal", params={"lookback_days": 30})
        assert resp.status_code == 200
        data = resp.json()
        assert data["signal_id"] == "drift-signal"

    async def test_evaluation_stats(self, client):
        resp = await client.get("/api/evaluations/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "pass_rate" in data
