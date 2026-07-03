"""Integration tests for Agent Recipe Compiler API with TestClient"""

import pytest
from unittest.mock import AsyncMock
from httpx import AsyncClient, ASGITransport

from src.database import RecipeDatabase
from src.api import app, get_db, get_chroma, get_ollama


@pytest.fixture
async def db():
    _db = RecipeDatabase(":memory:")
    yield _db
    await _db.close()


@pytest.fixture
def mock_chroma():
    m = AsyncMock()
    m.add_document = AsyncMock(return_value=True)
    m.search = AsyncMock(return_value=[])
    m.count = AsyncMock(return_value=0)
    return m


@pytest.fixture
def mock_ollama():
    m = AsyncMock()
    m.generate_with_grammar = AsyncMock(return_value='{"valid": "json"}')
    m.generate = AsyncMock(return_value="mock response")
    return m


@pytest.fixture
async def client(db, mock_chroma, mock_ollama):
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_chroma] = lambda: mock_chroma
    app.dependency_overrides[get_ollama] = lambda: mock_ollama

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


class TestRecipeAPI:
    async def test_health_check(self, client):
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "agent-recipe-compiler"

    async def test_capture_recipe(self, client):
        payload = {
            "objective": "classify_paper",
            "model": "qwen3.5",
            "prompt_version": 5,
            "memory_version": 12,
        }
        resp = await client.post("/api/recipes", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert "recipe_id" in data
        assert data["status"] == "captured"

    async def test_capture_recipe_rejects_invalid(self, client):
        resp = await client.post("/api/recipes", json={"objective": ""})
        assert resp.status_code == 422

    async def test_capture_recipe_full(self, client):
        payload = {
            "objective": "test_full",
            "model": "llama3",
            "prompt_version": 3,
            "memory_version": 8,
            "retrieved_docs": ["doc_1"],
            "reasoning_patterns": ["analyze"],
            "evaluation": {"score": 0.95, "reviewed_by": "expert"},
            "outcome": "accepted",
            "metadata": {"env": "test"},
        }
        resp = await client.post("/api/recipes", json=payload)
        assert resp.status_code == 201

    async def test_get_recipe(self, client):
        payload = {
            "objective": "get_test",
            "model": "test-model",
            "prompt_version": 1,
            "memory_version": 2,
        }
        create = await client.post("/api/recipes", json=payload)
        recipe_id = create.json()["recipe_id"]

        resp = await client.get(f"/api/recipes/{recipe_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["recipe_id"] == recipe_id
        assert data["objective"] == "get_test"
        assert data["outcome"] == "pending"

    async def test_get_recipe_not_found(self, client):
        resp = await client.get("/api/recipes/nonexistent")
        assert resp.status_code == 404

    async def test_list_recipes(self, client):
        resp = await client.get("/api/recipes")
        assert resp.status_code == 200
        data = resp.json()
        assert "recipes" in data
        assert "total" in data

    async def test_search_recipes(self, client):
        await client.post("/api/recipes", json={
            "objective": "search_target_document",
            "model": "qwen3.5",
            "prompt_version": 1,
            "memory_version": 1,
        })
        resp = await client.get("/api/recipes/search", params={"q": "search_target"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) >= 1
        assert data["query"] == "search_target"

    async def test_recipe_stats(self, client):
        resp = await client.get("/api/recipes/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "accepted" in data

    async def test_export_json(self, client):
        resp = await client.get("/api/recipes/export", params={"format": "json"})
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/json"

    async def test_export_csv(self, client):
        resp = await client.get("/api/recipes/export", params={"format": "csv"})
        assert resp.status_code == 200
        assert "csv" in resp.headers["content-type"]

    async def test_full_lifecycle(self, client):
        payload = {
            "objective": "lifecycle_test",
            "model": "test-model",
            "prompt_version": 2,
            "memory_version": 3,
            "retrieved_docs": ["doc_a", "doc_b"],
            "reasoning_patterns": ["compare", "synthesize"],
            "outcome": "accepted",
        }
        create = await client.post("/api/recipes", json=payload)
        recipe_id = create.json()["recipe_id"]

        get = await client.get(f"/api/recipes/{recipe_id}")
        assert get.json()["objective"] == "lifecycle_test"

        stats = await client.get("/api/recipes/stats")
        assert stats.json()["total"] >= 1
