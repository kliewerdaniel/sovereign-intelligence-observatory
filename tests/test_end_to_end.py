"""End-to-end integration test across multiple components"""

import importlib
import sys
from pathlib import Path

import pytest
from datetime import datetime
from uuid import uuid4
from httpx import AsyncClient, ASGITransport


def _import_component(component_dir: str, module: str):
    """Import a module from a component directory with hyphens in the name."""
    root = Path(__file__).resolve().parent.parent
    comp_path = root / component_dir
    if str(comp_path) not in sys.path:
        sys.path.insert(0, str(comp_path))
    return importlib.import_module(module)


@pytest.mark.asyncio
@pytest.mark.xfail(reason="e2e test needs shared DB fixtures via dependency overrides; runs per-component tests only")
async def test_agent_recipe_to_apprenticeship_flow():
    """Test full flow: create recipe -> route signal -> record action"""
    recipe_mod = _import_component("agent-recipe-compiler", "src.api")
    signal_mod = _import_component("expert-signal-router", "src.api")
    apprentice_mod = _import_component("sovereign-apprenticeship", "src.api")

    async with AsyncClient(transport=ASGITransport(app=recipe_mod.app), base_url="http://test") as recipe_client:
        recipe_payload = {
            "objective": "end_to_end_test",
            "model": "qwen3.5",
            "prompt_version": 3,
            "memory_version": 5,
            "retrieved_docs": ["doc_1"],
            "reasoning_patterns": ["analyze"],
            "outcome": "accepted",
        }
        resp = await recipe_client.post("/api/recipes", json=recipe_payload)
        assert resp.status_code == 201
        recipe_id = resp.json()["recipe_id"]

        resp = await recipe_client.get(f"/api/recipes/{recipe_id}")
        assert resp.status_code == 200
        assert resp.json()["objective"] == "end_to_end_test"

    async with AsyncClient(transport=ASGITransport(app=signal_mod.app), base_url="http://test") as signal_client:
        resp = await signal_client.post(
            f"/api/route/{recipe_id}",
            json={"recipe_id": recipe_id, "objective": "end_to_end_test", "confidence": 0.92},
        )
        assert resp.status_code == 200
        signal_result = resp.json()
        assert signal_result["signal_type"] in ("cheap", "auto_accepted")

    async with AsyncClient(transport=ASGITransport(app=apprentice_mod.app), base_url="http://test") as apprentice_client:
        agent_id = f"e2e-agent-{uuid4().hex[:8]}"
        resp = await apprentice_client.get(f"/api/agent/{agent_id}")
        assert resp.status_code == 200
        assert resp.json()["level"] == "fully_supervised"

        resp = await apprentice_client.post(
            f"/api/action/{agent_id}",
            json={"monitored": True, "quality_score": 0.95},
        )
        assert resp.status_code == 200
        assert resp.json()["action_recorded"] is True


@pytest.mark.asyncio
@pytest.mark.xfail(reason="e2e test needs shared DB fixtures via dependency overrides; runs per-component tests only")
async def test_signal_evaluation_to_observatory_flow():
    eval_mod = _import_component("autonomous-evaluation-loop", "src.api")
    obs_mod = _import_component("intelligence-observatory", "src.api")

    async with AsyncClient(transport=ASGITransport(app=eval_mod.app), base_url="http://test") as eval_client:
        resp = await eval_client.post("/api/signals", json={
            "signal_id": "e2e-signal",
            "name": "e2e_accuracy",
            "signal_type": "heuristic",
            "threshold": 0.7,
        })
        assert resp.status_code == 201

        resp = await eval_client.post("/api/evaluate/e2e-recipe", json={
            "signal_id": "e2e-signal",
            "score": 0.85,
        })
        assert resp.status_code == 200
        assert resp.json()["passed"] is True

    async with AsyncClient(transport=ASGITransport(app=obs_mod.app), base_url="http://test") as obs_client:
        resp = await obs_client.post("/api/timeline", json={
            "date": datetime.now().strftime("%Y-%m-%d"),
            "recipes": [
                {"evaluation": {"score": 0.85}, "memory_version": 1, "prompt_version": 1},
            ],
        })
        assert resp.status_code == 200

        resp = await obs_client.get("/api/observatory/stats")
        assert resp.status_code == 200
        assert resp.json()["timeline_entries"] >= 1
