"""Saturated Outbox Circuit Breaker integration tests.

Verifies that when the federated outbox queue reaches the configured
capacity limit, the Apprenticeship Engine freezes execution by returning
``circuit_breaked=True`` from ``record_action``.

NOTE: imports from sovereign-apprenticeship/src only to avoid
conflicts with other component src packages.
"""

import importlib
import sys
from pathlib import Path

import pytest

# Add sovereign-apprenticeship so src.* resolves correctly.
_APPR_DIR = Path(__file__).resolve().parent.parent / "sovereign-apprenticeship"
# Always re-insert at front; ensure it stays first even when another
# test file already added a different src root.
if str(_APPR_DIR) in sys.path:
    sys.path.remove(str(_APPR_DIR))
sys.path.insert(0, str(_APPR_DIR))


def _import_appr(mod_name: str):
    """Import a module from sovereign-apprenticeship/src, clearing stale
    ``src`` from sys.modules first to avoid cross-component conflicts.
    """
    for key in list(sys.modules):
        if key == "src" or key.startswith("src."):
            del sys.modules[key]
    # Ensure our target dir is first on sys.path.
    if str(_APPR_DIR) in sys.path:
        sys.path.remove(str(_APPR_DIR))
    sys.path.insert(0, str(_APPR_DIR))
    return importlib.import_module(mod_name)


class TestOutboxCircuitBreaker:
    """Verify outbox saturation freezes apprenticeship actions."""

    @pytest.fixture
    def appr_db_cls(self):
        db_mod = _import_appr("src.database")
        return db_mod.ApprenticeshipDatabase, db_mod.OUTBOX_CIRCUIT_BREAKER_LIMIT

    @pytest.fixture
    def appr_api(self):
        api_mod = _import_appr("src.api")
        return api_mod.app, api_mod.wire_outbox

    async def test_circuit_breaker_blocks_action(self, appr_db_cls):
        from shared.federated_sync import OutboxStore, FederatedPayload

        AppDB, LIMIT = appr_db_cls
        outbox = OutboxStore()
        for i in range(LIMIT + 10):
            payload = FederatedPayload(nodes=[], source_agent_id="a", domain="test")
            outbox.enqueue(payload, "http://down-peer:8000", max_retries=1)

        db = AppDB(outbox=outbox)
        result = await db.record_action("agent-1", monitored=True, quality_score=0.9)

        assert result["circuit_breaked"] is True
        assert result["action_recorded"] is False
        assert result["outbox_pending"] >= LIMIT
        await db.close()
        outbox.close()

    async def test_circuit_breaker_allows_action_when_queue_low(self, appr_db_cls):
        from shared.federated_sync import OutboxStore

        AppDB, _ = appr_db_cls
        outbox = OutboxStore()
        db = AppDB(outbox=outbox)
        result = await db.record_action("agent-2", monitored=True, quality_score=0.9)

        assert result["circuit_breaked"] is False
        assert result["action_recorded"] is True
        await db.close()
        outbox.close()

    async def test_circuit_breaker_endpoint_returns_status(self, appr_api, appr_db_cls):
        from shared.federated_sync import OutboxStore, FederatedPayload
        from fastapi.testclient import TestClient

        _, LIMIT = appr_db_cls
        app, wire_outbox = appr_api

        outbox = OutboxStore()
        for i in range(LIMIT + 5):
            p = FederatedPayload(nodes=[], source_agent_id="a", domain="test")
            outbox.enqueue(p, "http://down-peer:8000")

        wire_outbox(outbox)
        client = TestClient(app)
        resp = client.get("/api/circuit-breaker/agent-cb")
        assert resp.status_code == 200
        data = resp.json()
        assert data["circuit_breaked"] is True
        assert data["outbox_pending"] >= LIMIT
        assert data["agent_id"] == "agent-cb"
        outbox.close()
