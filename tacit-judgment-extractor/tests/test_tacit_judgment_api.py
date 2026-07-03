"""Integration tests for Tacit Judgment Extractor API"""

import pytest
from unittest.mock import AsyncMock
from httpx import AsyncClient, ASGITransport

from src.database import TacitJudgmentDatabase
from src.api import app, get_db, get_ollama
from src.models import ReasoningPattern


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


@pytest.fixture
async def client_no_ollama(db):
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_ollama] = lambda: None

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

    async def test_analyze_returns_reasoning_patterns(self, client):
        await client.post("/api/sessions", json={
            "session_id": "session-reason",
            "expert_id": "expert-5",
            "domain": "engineering",
            "session_text": "If pressure drops, check the valve. Usually this means a leak.",
        })
        resp = await client.post("/api/sessions/session-reason/analyze")
        assert resp.status_code == 200
        data = resp.json()
        assert "reasoning_patterns" in data

    async def test_create_expert_session(self, client):
        resp = await client.post("/api/expert/session", json={
            "session_id": "expert-session-1",
            "expert_id": "dr-smith",
            "domain": "cardiology",
            "session_text": "When patient has chest pain, always run an ECG first.",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["session_id"] == "expert-session-1"
        assert data["status"] == "recording"

    async def test_create_expert_session_then_get(self, client):
        await client.post("/api/expert/session", json={
            "session_id": "expert-session-get",
            "expert_id": "dr-jones",
            "domain": "neurology",
            "session_text": "Check reflexes and pupil response.",
        })
        resp = await client.get("/api/sessions/expert-session-get")
        assert resp.status_code == 200
        assert resp.json()["domain"] == "neurology"

    async def test_export_tree_by_id_not_found(self, client):
        resp = await client.get("/api/expert/trees/nonexistent-tree/export")
        assert resp.status_code == 404

    async def test_export_tree_by_id_after_analysis(self, client):
        await client.post("/api/expert/session", json={
            "session_id": "tree-export-test",
            "expert_id": "expert-6",
            "domain": "aviation",
            "session_text": "If engine temp exceeds 200C, throttle back immediately.",
        })
        analyze = await client.post("/api/sessions/tree-export-test/analyze")
        assert analyze.status_code == 200
        tree = analyze.json().get("decision_tree")
        assert tree is not None
        tree_id = tree["tree_id"]

        resp = await client.get(f"/api/expert/trees/{tree_id}/export")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tree_id"] == tree_id
        assert data["session_id"] == "tree-export-test"
        assert len(data["nodes"]) >= 1

    async def test_list_expert_sessions(self, client):
        await client.post("/api/expert/session", json={
            "session_id": "expert-list-1",
            "expert_id": "dr-alpha",
            "domain": "radiology",
            "session_text": "Look for nodules in upper lobes.",
        })
        resp = await client.get("/api/sessions?expert_id=dr-alpha")
        assert resp.status_code == 200
        data = resp.json()
        assert any(s["session_id"] == "expert-list-1" for s in data)

    async def test_expert_session_analyze_without_ollama(self, client_no_ollama):
        resp = await client_no_ollama.post("/api/expert/session", json={
            "session_id": "no-ollama-session",
            "expert_id": "expert-7",
            "domain": "general",
            "session_text": "Always check the oil level before starting.",
        })
        assert resp.status_code == 201

        analyze = await client_no_ollama.post("/api/sessions/no-ollama-session/analyze")
        assert analyze.status_code == 200
        data = analyze.json()
        assert len(data["patterns"]) >= 1
        assert data["status"] == "complete"
        assert "reasoning_patterns" in data

    async def test_expert_session_duplicate(self, client):
        payload = {
            "session_id": "dup-session",
            "expert_id": "expert-dup",
            "domain": "physics",
            "session_text": "Test content.",
        }
        resp1 = await client.post("/api/expert/session", json=payload)
        assert resp1.status_code == 201
        resp2 = await client.post("/api/expert/session", json=payload)
        assert resp2.status_code == 409

    async def test_correction_with_expert_session(self, client):
        await client.post("/api/expert/session", json={
            "session_id": "expert-corr",
            "expert_id": "dr-beta",
            "domain": "pharmacology",
            "session_text": "Initial dosage assessment.",
        })
        resp = await client.post(
            "/api/sessions/expert-corr/corrections",
            params={
                "original_text": "Initial dosage assessment.",
                "corrected_text": "Adjusted for renal function.",
                "rationale": "Patient has reduced kidney function.",
            },
        )
        assert resp.status_code == 200
        assert "correction_id" in resp.json()

    async def test_export_tree_contains_valid_nodes(self, client):
        await client.post("/api/expert/session", json={
            "session_id": "valid-tree-test",
            "expert_id": "expert-8",
            "domain": "chemistry",
            "session_text": "If pH is below 7, add base until neutralized.",
        })
        analyze = await client.post("/api/sessions/valid-tree-test/analyze")
        tree = analyze.json().get("decision_tree")
        assert tree is not None
        for node in tree["nodes"]:
            assert "node_id" in node
            assert "condition" in node
            assert "action" in node

    async def test_session_correction_not_found(self, client):
        resp = await client.post(
            "/api/sessions/nonexistent-corr/corrections",
            params={
                "original_text": "test",
                "corrected_text": "fixed",
                "rationale": "because",
            },
        )
        assert resp.status_code == 404

    async def test_full_expert_lifecycle(self, client):
        sid = "full-lifecycle"
        await client.post("/api/expert/session", json={
            "session_id": sid,
            "expert_id": "expert-life",
            "domain": "logistics",
            "session_text": "If delivery is delayed by more than 2 hours, escalate to supervisor.",
        })
        await client.post(f"/api/sessions/{sid}/corrections", params={
            "original_text": "2 hours",
            "corrected_text": "1 hour for priority shipments",
            "rationale": "Priority tier added",
        })
        analyze = await client.post(f"/api/sessions/{sid}/analyze")
        assert analyze.status_code == 200
        data = analyze.json()
        assert data["session_id"] == sid
        assert len(data["patterns"]) >= 1
        assert len(data.get("reasoning_patterns", [])) >= 0
        tree = data.get("decision_tree")
        if tree:
            export_resp = await client.get(f"/api/expert/trees/{tree['tree_id']}/export")
            assert export_resp.status_code == 200

    async def test_reasoning_patterns_contain_expected_fields(self, client):
        await client.post("/api/expert/session", json={
            "session_id": "reason-fields",
            "expert_id": "expert-9",
            "domain": "education",
            "session_text": "Students who struggle with fundamentals typically need remedial work.",
        })
        analyze = await client.post("/api/sessions/reason-fields/analyze")
        data = analyze.json()
        for rp in data.get("reasoning_patterns", []):
            assert "pattern_type" in rp
            assert "confidence" in rp
            assert "antecedents" in rp
            assert "consequents" in rp
