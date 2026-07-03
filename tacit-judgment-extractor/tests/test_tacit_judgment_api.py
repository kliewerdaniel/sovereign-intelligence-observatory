"""Integration tests for Tacit Judgment Extractor API"""

import pytest
from unittest.mock import AsyncMock
from httpx import AsyncClient, ASGITransport

from src.database import TacitJudgmentDatabase
from src.api import app, get_db, get_ollama


@pytest.fixture
async def db():
    _db = TacitJudgmentDatabase(":memory:")
    yield _db
    await _db.close()


@pytest.fixture
def mock_ollama():
    m = AsyncMock()
    m.generate = AsyncMock(return_value="Extracted pattern: conditional check")
    return m


@pytest.fixture
async def client(db, mock_ollama):
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_ollama] = lambda: mock_ollama

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


class TestTacitJudgmentAPI:
    async def test_health(self, client):
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["service"] == "tacit-judgment-extractor"

    async def test_create_session(self, client):
        resp = await client.post("/api/sessions", json={
            "session_id": "session-1",
            "expert_id": "expert-1",
            "domain": "medical_diagnosis",
            "session_text": "When patient presents with fever and cough, I always check for pneumonia first.",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["session_id"] == "session-1"
        assert data["status"] == "recording"

    async def test_get_session(self, client):
        await client.post("/api/sessions", json={
            "session_id": "session-2",
            "expert_id": "expert-1",
            "domain": "legal_review",
            "session_text": "Standard contract review procedure.",
        })
        resp = await client.get("/api/sessions/session-2")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == "session-2"
        assert data["domain"] == "legal_review"

    async def test_get_session_not_found(self, client):
        resp = await client.get("/api/sessions/nonexistent")
        assert resp.status_code == 404

    async def test_list_sessions(self, client):
        resp = await client.get("/api/sessions")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_add_correction(self, client):
        await client.post("/api/sessions", json={
            "session_id": "session-corr",
            "expert_id": "expert-2",
            "domain": "finance",
            "session_text": "Initial assessment.",
        })
        resp = await client.post(
            "/api/sessions/session-corr/corrections",
            params={
                "original_text": "Initial assessment.",
                "corrected_text": "Revised assessment with risk calculation.",
                "rationale": "Added risk factor analysis.",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "correction_id" in data

    async def test_analyze_session(self, client):
        await client.post("/api/sessions", json={
            "session_id": "session-analyze",
            "expert_id": "expert-3",
            "domain": "cybersecurity",
            "session_text": "When I see unusual outbound traffic, I always check for data exfiltration.",
        })
        resp = await client.post("/api/sessions/session-analyze/analyze")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == "session-analyze"
        assert len(data["patterns"]) >= 1
        assert data["status"] == "complete"

    async def test_export_decision_tree(self, client):
        await client.post("/api/sessions", json={
            "session_id": "session-tree",
            "expert_id": "expert-4",
            "domain": "manufacturing",
            "session_text": "If temperature exceeds threshold, shut down the line.",
        })
        await client.post("/api/sessions/session-tree/analyze")
        resp = await client.get("/api/sessions/session-tree/tree")
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert len(data["nodes"]) >= 1
