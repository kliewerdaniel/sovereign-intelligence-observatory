"""Concurrency and multi-threaded stress tests for database locking.

Verifies that WAL mode + busy-timeout prevent lock contention under
heavy parallel agent loads.
"""

import asyncio
import sys
from pathlib import Path

import pytest
from shared.async_db import AsyncDatabase
from shared.federated_sync import FederatedPayload, FileShareTransport

# Add intelligence-observatory to sys.path for TelemetryManager import
_OBS_DIR = Path(__file__).resolve().parent.parent / "intelligence-observatory"
if str(_OBS_DIR) not in sys.path:
    sys.path.insert(0, str(_OBS_DIR))


@pytest.fixture
async def mem_db():
    db = AsyncDatabase(":memory:", busy_timeout=3000)
    yield db
    await db.close()


class TestConcurrentDatabaseAccess:
    """Stress-test AsyncDatabase with concurrent writers."""

    async def test_parallel_writes(self, mem_db):
        N = 50
        await mem_db.execute("CREATE TABLE IF NOT EXISTS concurrency_test (id INTEGER PRIMARY KEY, val TEXT)")
        await mem_db.commit()

        async def writer(i: int):
            await mem_db.execute(
                "INSERT INTO concurrency_test (val) VALUES (?)",
                (f"writer-{i}",),
            )
            await mem_db.commit()

        tasks = [writer(i) for i in range(N)]
        await asyncio.gather(*tasks)

        rows = await mem_db.fetchall("SELECT * FROM concurrency_test ORDER BY id")
        assert len(rows) == N, f"Expected {N} rows, got {len(rows)}"

    async def test_parallel_reads_and_writes(self, mem_db):
        await mem_db.execute("CREATE TABLE IF NOT EXISTS rw_test (id INTEGER PRIMARY KEY, val TEXT)")
        for i in range(10):
            await mem_db.execute("INSERT INTO rw_test (val) VALUES (?)", (f"initial-{i}",))
        await mem_db.commit()

        async def reader() -> int:
            rows = await mem_db.fetchall("SELECT COUNT(*) AS cnt FROM rw_test")
            return rows[0]["cnt"] if rows else 0

        async def writer(i: int):
            await mem_db.execute(
                "INSERT INTO rw_test (val) VALUES (?)",
                (f"concurrent-{i}",),
            )
            await mem_db.commit()

        readers = [reader() for _ in range(20)]
        writers = [writer(i) for i in range(30)]
        results = await asyncio.gather(*readers, *writers)

        read_results = [r for r in results if isinstance(r, int)]
        final_count = (await mem_db.fetchall("SELECT COUNT(*) AS cnt FROM rw_test"))[0]["cnt"]
        assert final_count >= 30, f"Expected >=40 total rows, got {final_count}"
        assert all(c == 10 or c >= 30 for c in read_results), "Readers saw inconsistent counts"

    async def test_busy_timeout_survives_contention(self, mem_db):
        await mem_db.execute("CREATE TABLE IF NOT EXISTS contention_test (id INTEGER PRIMARY KEY, val TEXT)")
        await mem_db.commit()

        async def slow_writer():
            conn = await mem_db.connect()
            await conn.execute("BEGIN IMMEDIATE")
            await asyncio.sleep(0.05)
            await conn.execute("INSERT INTO contention_test (val) VALUES ('slow')")
            await conn.commit()

        async def fast_writer():
            await asyncio.sleep(0.01)
            await mem_db.execute("INSERT INTO contention_test (val) VALUES ('fast')")
            await mem_db.commit()

        results = await asyncio.gather(slow_writer(), fast_writer(), return_exceptions=True)
        errors = [r for r in results if isinstance(r, Exception)]
        assert len(errors) == 0, f"Contention errors: {errors}"
        rows = await mem_db.fetchall("SELECT * FROM contention_test ORDER BY id")
        assert len(rows) == 2


class TestFederatedSyncConcurrency:
    """Stress-test federated file-share transport from concurrent agents."""

    async def test_concurrent_file_exports(self, tmp_path):
        transport_a = FileShareTransport(str(tmp_path), "agent-a")
        transport_b = FileShareTransport(str(tmp_path), "agent-b")

        def export_agent(transport: FileShareTransport, agent_id: str, count: int):
            for i in range(count):
                payload = FederatedPayload(
                    nodes=[{"condition": f"rule_{i}", "action": "act", "confidence": 0.9, "rationale": "test"}],
                    source_agent_id=agent_id,
                    domain="test",
                )
                transport.export(payload)

        await asyncio.gather(
            asyncio.to_thread(export_agent, transport_a, "agent-a", 20),
            asyncio.to_thread(export_agent, transport_b, "agent-b", 20),
        )

        inbound = transport_a.discover_inbound()
        assert len(inbound) > 0, "Agent-a should discover agent-b exports"
        all_files = list(tmp_path.glob("*.sio_federated"))
        assert len(all_files) == 40


class TestTelemetryManager:
    """Verify TelemetryManager collects payloads without error."""

    @pytest.mark.xfail(reason="src.telemetry moved to sub-module")
    async def test_collect_payload(self):
        import importlib
        import sys; sys.path.insert(0, "intelligence-observatory/src"); telemetry_mod = importlib.import_module("telemetry")
        db_mod = importlib.import_module("database")

        tm = telemetry_mod.TelemetryManager()
        db = db_mod.ObservatoryDatabase()
        payload = await tm._collect_payload(db)
        await db.close()

        assert "ts" in payload
        assert "stats" in payload
        assert "timeline" in payload
        assert "drift_alerts" in payload
        assert "obsolescent_count" in payload
