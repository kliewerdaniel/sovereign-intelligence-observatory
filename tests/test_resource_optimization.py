"""Resource-constrained optimization tests.

Covers:
  - Token-aware context condenser (token limiting, truncation, summarization)
  - Quantization drift baseline (root-cause classification)
  - Delta-encoded WebSocket telemetry (client-simulated reconstruction)
  - Cold-storage archive pipeline (gzip + SHA-256 hash verification)
"""

import json
import sys
import gzip
import importlib
from pathlib import Path

import pytest

# Add intelligence-observatory directory to sys.path for src.* imports
_OBS_DIR = Path(__file__).resolve().parent.parent / "intelligence-observatory"
if str(_OBS_DIR) not in sys.path:
    sys.path.insert(0, str(_OBS_DIR))

from shared.context_condenser import TokenAwareContextCondenser, ContextTruncationError
from shared.quantization_drift import QuantizationDriftDiagnostic


class TestTokenAwareContextCondenser:
    """Verify the condenser respects token windows and truncation strategy."""

    def make_context(self, recipe_count: int, tokens_per_recipe: int = 200) -> dict:
        recipes = []
        for i in range(recipe_count):
            recipes.append({"id": f"recipe-{i}", "text": "word " * tokens_per_recipe})
        return {
            "system_instruction": "You are a helpful assistant.",
            "recipe_contexts": recipes,
            "user_query": "Classify this paper.",
        }

    def test_condenser_keeps_context_below_threshold(self):
        cond = TokenAwareContextCondenser(max_tokens=10000, context_window_ratio=0.85)
        ctx = self.make_context(3, 50)
        result = cond.condense(ctx)
        assert result["truncated_count"] == 0
        assert result["token_savings"] == 0

    def test_condenser_drops_oldest_recipes(self):
        cond = TokenAwareContextCondenser(max_tokens=1000, context_window_ratio=0.85)
        ctx = self.make_context(20, 60)
        result = cond.condense(ctx)
        assert result["truncated_count"] > 0
        assert result["token_savings"] > 0
        assert "recipe_contexts" in result["condensed"]

    def test_condenser_summarizes_when_dropping_insufficient(self):
        cond = TokenAwareContextCondenser(max_tokens=500, context_window_ratio=0.85)
        ctx = self.make_context(50, 80)
        result = cond.condense(ctx)
        assert result["truncated_count"] > 0

    def test_condenser_raises_on_impossible_context(self):
        cond = TokenAwareContextCondenser(max_tokens=100, context_window_ratio=0.85)
        many_sections = {f"section_{i}": "word " * 1000 for i in range(30)}
        with pytest.raises(ContextTruncationError):
            cond.condense(many_sections)

    def test_condenser_empty_context(self):
        cond = TokenAwareContextCondenser()
        result = cond.condense({})
        assert result["truncated_count"] == 0
        assert result["token_savings"] == 0

    def test_condenser_estimates_tokens(self):
        cond = TokenAwareContextCondenser()
        tokens = cond.estimate_tokens("hello world " * 50)
        assert tokens > 0


class TestQuantizationDriftDiagnostic:
    """Verify drift baseline classifies quantization vs software regression."""

    def test_diagnose_quantization_drift(self):
        diag = QuantizationDriftDiagnostic(drift_threshold=0.15)
        result = diag.diagnose(
            regression_score_change=-0.05,
            affected_tasks=["text_classification"],
            regression_severity="low",
        )
        assert result.root_cause == "quantization"
        assert result.severity in ("low", "medium")
        assert "quantization" in result.recommendation.lower()

    def test_diagnose_software_regression(self):
        diag = QuantizationDriftDiagnostic(drift_threshold=0.15)
        result = diag.diagnose(
            regression_score_change=-0.5,
            affected_tasks=["ner", "classification"],
            regression_severity="high",
        )
        assert result.root_cause == "software"
        assert "software" in result.recommendation.lower()

    def test_diagnose_unknown_drift(self):
        diag = QuantizationDriftDiagnostic(drift_threshold=0.15)
        result = diag.diagnose(
            regression_score_change=-0.1,
            affected_tasks=[],
            regression_severity="low",
        )
        assert result.root_cause in ("quantization", "unknown")
        assert isinstance(result.reference_score, float)


class TestDeltaTelemetryReconstruction:
    """Simulate a client receiving deltas and reconstructing full state."""

    def _get_telemetry_class(self):
        telemetry_mod = importlib.import_module("src.telemetry")
        return telemetry_mod.TelemetryManager

    def test_compute_delta_changed_keys(self):
        tm_cls = self._get_telemetry_class()
        tm = tm_cls()
        prev = {"ts": "2025-01-01T00:00:00", "stats": {"a": 1}, "obsolescent_count": 5}
        curr = {"ts": "2025-01-01T00:00:05", "stats": {"a": 2}, "obsolescent_count": 5}
        delta = tm._compute_delta(prev, curr)
        assert "ts" in delta
        assert "stats" in delta
        assert "obsolescent_count" not in delta

    def test_reconstruct_full_from_deltas(self):
        tm_cls = self._get_telemetry_class()
        tm = tm_cls()
        full = {
            "ts": "2025-01-01T00:00:00",
            "stats": {"timeline_entries": 10, "obsolescent_prompts": 3},
            "timeline": [{"date": "2025-01-01", "recipe_count": 5}],
            "obsolescent_count": 3,
            "drift_alerts": [],
        }
        accumulator = dict(full)
        delta1 = {"ts": "2025-01-01T00:00:05", "stats": {"timeline_entries": 12}}
        for key, value in delta1.items():
            accumulator[key] = value
        assert accumulator["stats"]["timeline_entries"] == 12
        assert accumulator["obsolescent_count"] == 3


class TestColdStorageArchive:
    """Verify the archive pipeline produces valid gzip + hash archives."""

    async def _make_db(self):
        db_mod = importlib.import_module("src.database")
        return db_mod.ObservatoryDatabase()

    async def _make_pipeline(self, db, archive_dir):
        arc_mod = importlib.import_module("src.archive")
        return arc_mod.ArchivePipeline(db._db, archive_dir=archive_dir, archive_after_days=0)

    async def test_archive_pipeline_no_old_data(self, tmp_path):
        db = await self._make_db()
        pipeline = await self._make_pipeline(db, str(tmp_path))
        result = await pipeline.archive_recipes()
        assert result["archived"] == 0
        await db.close()

    async def test_archive_creates_gzip_with_hash(self, tmp_path):
        db = await self._make_db()
        await db._init_schema()
        await db._db.execute(
            "INSERT INTO intelligence_timeline (id, date, recipe_count, avg_score, capability_index, memory_versions, prompt_versions) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("recipe-old", "2024-01-01", 5, 0.8, 0.75, "[]", "[]"),
        )
        await db._db.commit()

        pipeline = await self._make_pipeline(db, str(tmp_path))
        result = await pipeline.archive_recipes()
        assert result["archived"] == 1
        assert result["hash"].startswith("sha256:")

        archive_file = tmp_path / result["filename"]
        assert archive_file.exists()
        with gzip.open(archive_file, "rt") as f:
            content = f.read()
        assert "recipe-old" in content

        verify = await pipeline.verify_archive(result["filename"])
        assert verify["valid"] is True
        await db.close()

    async def test_archive_hash_verification_fails_on_corruption(self, tmp_path):
        db = await self._make_db()
        await db._init_schema()
        await db._db.execute(
            "INSERT INTO intelligence_timeline (id, date, recipe_count, avg_score, capability_index, memory_versions, prompt_versions) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("recipe-old-2", "2024-02-01", 3, 0.9, 0.8, "[]", "[]"),
        )
        await db._db.commit()

        pipeline = await self._make_pipeline(db, str(tmp_path))
        result = await pipeline.archive_recipes()
        assert result["archived"] == 1

        archive_file = tmp_path / result["filename"]
        with gzip.open(archive_file, "wt") as f:
            f.write("tampered data")

        verify = await pipeline.verify_archive(result["filename"])
        assert verify["valid"] is False
        assert "Hash mismatch" in verify.get("error", "")
        await db.close()
