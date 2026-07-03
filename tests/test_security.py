"""Security integration tests for sandbox isolation, tenant
separation, and safe maintenance concurrency.

Test categories:
1. Action sandbox — blocklisted patterns, resource limits, timeouts.
2. Vector tenant isolation — agent_id-partitioned collections.
3. Background maintenance — VACUUM/optimize concurrency safety.
"""

import asyncio
import tempfile
from pathlib import Path

import pytest

from shared.sandbox import ActionSandbox, SandboxViolation
from shared.chroma_client import ChromaClient


# ── 1. Action Sandbox ─────────────────────────────────────────────────────────

class TestActionSandbox:
    """Verify that dangerous operations are rejected or contained."""

    @pytest.fixture
    def sandbox(self):
        return ActionSandbox(max_cpu=2, max_memory_mb=32, timeout_s=5)

    async def test_allows_safe_code(self, sandbox):
        result = await sandbox.execute("x = 1 + 1")
        assert result["success"] is True
        assert result["sandboxed"] is True

    async def test_rejects_os_import(self, sandbox):
        with pytest.raises(SandboxViolation, match="import os"):
            await sandbox.execute("import os; os.system('echo pwned')")

    async def test_rejects_subprocess_import(self, sandbox):
        with pytest.raises(SandboxViolation, match="import subprocess"):
            await sandbox.execute("import subprocess; subprocess.run(['ls'])")

    async def test_rejects_eval_call(self, sandbox):
        with pytest.raises(SandboxViolation, match="eval"):
            await sandbox.execute("eval('1+1')")

    async def test_rejects_exec_call(self, sandbox):
        with pytest.raises(SandboxViolation, match="exec"):
            await sandbox.execute("exec('x=1')")

    async def test_rejects_blocklisted_open(self, sandbox):
        with pytest.raises(SandboxViolation, match="open"):
            await sandbox.execute("f = open('/etc/passwd')")

    async def test_rejects_getattr_escape(self, sandbox):
        with pytest.raises(SandboxViolation, match="getattr"):
            await sandbox.execute("getattr(obj, '__class__')")

    async def test_times_out_long_running_code(self, sandbox):
        sandbox_fast = ActionSandbox(max_cpu=1, timeout_s=1)
        result = await sandbox_fast.execute("import time; time.sleep(10)")
        assert result["timed_out"] is True
        assert result["success"] is False

    async def test_context_passed_to_action(self, sandbox):
        result = await sandbox.execute(
            'print(context.get("key", "none"))',
            context={"key": "hello_sandbox"},
        )
        assert result["success"] is True
        assert "hello_sandbox" in result["stdout"]

    @pytest.mark.skip(reason="Platform-specific memory enforcement")
    async def test_memory_limit_enforced(self, sandbox):
        sandbox_tight = ActionSandbox(max_memory_mb=1, timeout_s=5)
        result = await sandbox_tight.execute("x = [0] * 10_000_000")
        assert result["success"] is False


# ── 2. Vector Tenant Isolation ────────────────────────────────────────────────

class TestChromaTenantIsolation:
    """Verify that different agent_ids produce distinct collection names."""

    def test_tenant_namespace_is_deterministic(self):
        c1 = ChromaClient(agent_id="agent-alpha")
        c2 = ChromaClient(agent_id="agent-alpha")
        assert c1.collection_name == c2.collection_name
        assert "___" in c1.collection_name

    def test_tenant_namespace_differs_per_agent(self):
        c1 = ChromaClient(agent_id="agent-alpha")
        c2 = ChromaClient(agent_id="agent-beta")
        assert c1.collection_name != c2.collection_name
        assert c1.collection_name.endswith("___") == c2.collection_name.endswith("___")

    def test_no_agent_id_uses_base_name(self):
        c = ChromaClient()
        assert "___" not in c.collection_name
        assert c.collection_name == "observatory_recipes"

    def test_tenant_collection_includes_base_name(self):
        c = ChromaClient(collection_name="my_recipes", agent_id="agent-42")
        assert c.collection_name.startswith("my_recipes___")

    def test_sha256_namespace_is_16_chars(self):
        c = ChromaClient(agent_id="agent-x")
        suffix = c.collection_name.split("___")[-1]
        assert len(suffix) == 16
        import hashlib
        expected = hashlib.sha256(b"agent-x").hexdigest()[:16]
        assert suffix == expected


# ── 3. Background Maintenance Concurrency ────────────────────────────────────

class TestMaintenanceConcurrency:
    """Verify that VACUUM/optimize doesn't break concurrent read/write."""

    async def test_optimize_does_not_block_reads(self, tmp_path):
        from shared.async_db import AsyncDatabase

        db_path = str(tmp_path / "test_maintenance.db")
        db = AsyncDatabase(db_path, busy_timeout=5000)
        await db.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY, v TEXT)")
        for i in range(100):
            await db.execute("INSERT INTO t (v) VALUES (?)", (f"val-{i}",))
        await db.commit()

        # Run maintenance while concurrently reading.
        async def reader():
            rows = await db.fetchall("SELECT COUNT(*) AS cnt FROM t")
            return rows[0]["cnt"]

        async def writer(i: int):
            await db.execute("INSERT INTO t (v) VALUES (?)", (f"concurrent-{i}",))
            await db.commit()

        maintenance_task = asyncio.create_task(db.run_maintenance(vacuum_threshold_mb=1))
        read_task = asyncio.create_task(reader())
        write_tasks = [writer(i) for i in range(20)]

        results = await asyncio.gather(maintenance_task, read_task, *write_tasks, return_exceptions=True)
        errors = [r for r in results if isinstance(r, Exception)]
        assert len(errors) == 0, f"Concurrent maintenance errors: {errors}"

        final = (await db.fetchall("SELECT COUNT(*) AS cnt FROM t"))[0]["cnt"]
        assert final >= 100, f"Lost rows during maintenance: {final}"
        await db.close()

    async def test_periodic_maintenance_loop(self, tmp_path):
        from shared.async_db import AsyncDatabase

        db_path = str(tmp_path / "test_periodic.db")
        db = AsyncDatabase(db_path)
        await db.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY, v TEXT)")
        for i in range(50):
            await db.execute("INSERT INTO t (v) VALUES (?)", (f"val-{i}",))
        await db.commit()

        task = await db.start_periodic_maintenance(interval_s=1, vacuum_threshold_mb=1)
        await asyncio.sleep(1.5)
        rows = await db.fetchall("SELECT COUNT(*) AS cnt FROM t")
        assert rows[0]["cnt"] == 50
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        await db.close()

    async def test_vacuum_on_large_db(self, tmp_path):
        from shared.async_db import AsyncDatabase

        db_path = str(tmp_path / "test_vacuum.db")
        db = AsyncDatabase(db_path)
        await db.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY, v TEXT)")
        for i in range(500):
            await db.execute("INSERT INTO t (v) VALUES (?)", (f"val-{i}",))
            await db.execute("DELETE FROM t WHERE id=?", (i,))
        await db.commit()

        await db.run_maintenance(vacuum_threshold_mb=0)
        # Should not raise.
        await db.close()

    async def test_outbox_retry_persistence(self):
        from shared.federated_sync import OutboxStore, FederatedPayload

        store = OutboxStore()
        payload = FederatedPayload(
            nodes=[{"condition": "test", "action": "act", "confidence": 0.9, "rationale": "r"}],
            source_agent_id="agent-a",
            domain="test",
        )
        row_id = store.enqueue(payload, "http://unreachable:9999")
        assert row_id > 0
        assert store.count_pending() == 1

        # Claim and retry — count should still be 1 (retry_count incremented).
        due = store.claim_due()
        assert len(due) == 1
        assert due[0]["retry_count"] == 0
        store.mark_retry(due[0]["id"], "Connection refused")
        assert store.count_pending() == 1

        # Verify retry_count was incremented.
        due2 = store.claim_due()
        # next_retry_at is in the future (2^1 = 2s), so claim_due returns empty.
        assert len(due2) == 0

        # Bypass backoff via direct SQL to test exhaustion logic.
        import sqlite3
        store._local.execute(
            "UPDATE federated_outbox SET retry_count=9, next_retry_at=0 WHERE id=?",
            (due[0]["id"],),
        )
        store._local.commit()

        due3 = store.claim_due()
        assert len(due3) == 1
        store.mark_retry(due3[0]["id"], "final failure")
        # retry_count 10 >= max_retries 10 -> acknowledged.
        assert store.count_pending() == 0

        store.close()
