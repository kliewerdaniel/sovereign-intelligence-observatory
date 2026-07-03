"""Ledger Security & Cluster Topology integration tests.

Covers:
  1. Sequential ledger chain — linking, verification, chain-break detection.
  2. On-demand archive streamer — single-record retrieval without full load.
  3. LAN peer discovery — module init, heartbeat, stale expiry.

NOTE: imports from intelligence-observatory/src only to avoid
conflicts with other component src packages.
"""

import asyncio
import gzip
import importlib
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

from shared.peer_discovery import PeerDiscovery, PeerInfo

# Add intelligence-observatory so src.* resolves correctly.
_OBS_DIR = Path(__file__).resolve().parent.parent / "intelligence-observatory"
if str(_OBS_DIR) not in sys.path:
    sys.path.insert(0, str(_OBS_DIR))


def _import_obs(mod_name: str):
    """Import a module from intelligence-observatory/src, clearing stale
    ``src`` from sys.modules first to avoid cross-component conflicts.
    """
    for key in list(sys.modules):
        if key == "src" or key.startswith("src."):
            del sys.modules[key]
    # Ensure our target dir is first on sys.path.
    if str(_OBS_DIR) in sys.path:
        sys.path.remove(str(_OBS_DIR))
    sys.path.insert(0, str(_OBS_DIR))
    return importlib.import_module(mod_name)


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def obs_db():
    db_mod = _import_obs("src.database")
    return db_mod.ObservatoryDatabase()


@pytest.fixture
def arc_pipeline(obs_db, tmp_path):
    arc_mod = _import_obs("src.archive")
    return arc_mod.ArchivePipeline(obs_db._db, archive_dir=str(tmp_path), archive_after_days=0)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Sequential Ledger Chain
# ═══════════════════════════════════════════════════════════════════════════════

class TestLedgerChain:
    """Verify archives are linked in a Merkle sequence and break detection."""

    async def _seed_recipe(self, db, recipe_id: str, date: str):
        await db._init_schema()
        await db._db.execute(
            "INSERT INTO intelligence_timeline (id, date, recipe_count, avg_score, "
            "capability_index, memory_versions, prompt_versions) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (recipe_id, date, 5, 0.8, 0.75, "[]", "[]"),
        )
        await db._db.commit()

    async def test_chain_links_two_archives(self, obs_db, arc_pipeline, tmp_path):
        await self._seed_recipe(obs_db, "r1", "2024-01-01")
        r1 = await arc_pipeline.archive_recipes()
        assert r1["archived"] == 1
        assert r1["previous_hash"] == ""

        await self._seed_recipe(obs_db, "r2", "2024-01-02")
        r2 = await arc_pipeline.archive_recipes()
        assert r2["archived"] == 1
        assert r2["previous_hash"] == r1["hash"]

    async def test_chain_verification_passes(self, obs_db, arc_pipeline, tmp_path):
        await self._seed_recipe(obs_db, "r3", "2024-01-03")
        await arc_pipeline.archive_recipes()
        await self._seed_recipe(obs_db, "r4", "2024-01-04")
        await arc_pipeline.archive_recipes()

        results = await arc_pipeline.verify_chain()
        assert len(results) == 2
        assert all(r["valid"] for r in results)

    async def test_chain_break_detected(self, obs_db, arc_pipeline, tmp_path):
        await self._seed_recipe(obs_db, "r5", "2024-01-05")
        await arc_pipeline.archive_recipes()
        await self._seed_recipe(obs_db, "r6", "2024-01-06")
        r2 = await arc_pipeline.archive_recipes()

        # Tamper with the first archive's metadata to break the chain.
        await obs_db._db.execute(
            "UPDATE cold_storage_archive SET hash = 'sha256:' || 'f' * 64 WHERE filename = ?",
            (r2["filename"],),
        )
        await obs_db._db.commit()

        results = await arc_pipeline.verify_chain()
        assert any(not r["valid"] for r in results)

    async def test_genesis_archive_no_previous(self, obs_db, arc_pipeline, tmp_path):
        await self._seed_recipe(obs_db, "r7", "2024-01-07")
        result = await arc_pipeline.archive_recipes()
        assert result["previous_hash"] == ""
        assert result["hash"] != ""


# ═══════════════════════════════════════════════════════════════════════════════
# 2. On-Demand Archive Streamer
# ═══════════════════════════════════════════════════════════════════════════════

class TestArchiveStreamer:
    """Verify streaming read retrieves records without full decompression."""

    async def _seed_recipes(self, obs_db, count: int = 5):
        await obs_db._init_schema()
        for i in range(count):
            rid = f"stream-r{i}"
            await obs_db._db.execute(
                "INSERT INTO intelligence_timeline (id, date, recipe_count, avg_score, "
                "capability_index, memory_versions, prompt_versions) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (rid, f"2024-03-{i+1:02d}", i + 1, 0.5 + i * 0.1, 0.6, "[]", "[]"),
            )
        await obs_db._db.commit()

    async def _get_streamer(self, archive_dir):
        arc_mod = _import_obs("src.archive")
        return arc_mod.ArchiveStreamer(archive_dir=archive_dir)

    async def test_streamer_finds_recipe_by_id(self, obs_db, arc_pipeline, tmp_path):
        await self._seed_recipes(obs_db, 10)
        result = await arc_pipeline.archive_recipes()
        assert result["archived"] == 10

        streamer = await self._get_streamer(str(tmp_path))
        found = streamer.find_recipe(result["filename"], "stream-r3")
        assert found is not None
        assert found.get("id") == "stream-r3"

    async def test_streamer_returns_none_for_missing(self, obs_db, arc_pipeline, tmp_path):
        await self._seed_recipes(obs_db, 3)
        result = await arc_pipeline.archive_recipes()

        streamer = await self._get_streamer(str(tmp_path))
        found = streamer.find_recipe(result["filename"], "nonexistent")
        assert found is None

    async def test_streamer_iterates_all_records(self, obs_db, arc_pipeline, tmp_path):
        await self._seed_recipes(obs_db, 7)
        result = await arc_pipeline.archive_recipes()

        streamer = await self._get_streamer(str(tmp_path))
        records = list(streamer.iter_archive(result["filename"]))
        assert len(records) == 7

    async def test_streamer_handles_missing_archive(self, tmp_path):
        streamer = await self._get_streamer(str(tmp_path))
        assert streamer.find_recipe("nonexistent.csv.gz", "r1") is None
        assert list(streamer.iter_archive("nonexistent.csv.gz")) == []


# ═══════════════════════════════════════════════════════════════════════════════
# 3. LAN Peer Discovery
# ═══════════════════════════════════════════════════════════════════════════════

class TestPeerDiscovery:
    """Verify peer discovery module initialises, heartbeats, and expires."""

    def test_peer_info_stale_check(self):
        p = PeerInfo(agent_id="a1", host="10.0.0.1", port=8000, last_seen=0)
        assert p.is_stale(timeout=1)

        p.last_seen = 1e12
        assert not p.is_stale(timeout=3600)

    def test_peers_property_filters_stale(self):
        pd = PeerDiscovery(agent_id="self", service_port=8000, timeout_s=1)
        pd._peers["fresh"] = PeerInfo("fresh", "10.0.0.2", 8001, last_seen=1e12)
        pd._peers["stale"] = PeerInfo("stale", "10.0.0.3", 8002, last_seen=0)
        active = pd.peers
        assert "fresh" in active
        assert "stale" not in active

    @pytest.mark.asyncio
    async def test_peers_empty_after_stop(self):
        pd = PeerDiscovery(agent_id="self", service_port=8000)
        assert pd.peer_count == 0
        await pd.stop()
        assert pd.peer_count == 0

    def test_build_announcement_contains_agent_id(self):
        pd = PeerDiscovery(agent_id="agent-x", service_port=9000)
        ann = pd._build_announcement()
        msg = json.loads(ann.decode())
        assert msg["agent_id"] == "agent-x"
        assert msg["port"] == 9000
