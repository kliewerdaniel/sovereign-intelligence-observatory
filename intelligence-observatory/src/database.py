"""Intelligence Observatory - Asynchronous Database Layer"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from shared.async_db import AsyncDatabase


class ObservatoryDatabase:
    def __init__(self, db_path: str = ":memory:"):
        self._db = AsyncDatabase(db_path)
        self._initialized = False

    async def _init_schema(self) -> None:
        if self._initialized:
            return
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS intelligence_timeline (
                id TEXT PRIMARY KEY,
                date TEXT NOT NULL,
                recipe_count INTEGER DEFAULT 0,
                avg_score REAL DEFAULT 0.0,
                capability_index REAL DEFAULT 1.0,
                memory_versions TEXT DEFAULT '[]',
                prompt_versions TEXT DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS obsolescent_prompts (
                prompt_id TEXT PRIMARY KEY,
                prompt_name TEXT NOT NULL,
                usage_count INTEGER DEFAULT 0,
                avg_relevance REAL DEFAULT 0.0,
                trend TEXT DEFAULT 'stable',
                last_used TEXT
            );

            CREATE TABLE IF NOT EXISTS unused_memories (
                memory_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                usage_count INTEGER DEFAULT 0,
                last_retrieved TEXT
            );

            CREATE TABLE IF NOT EXISTS signal_correlations (
                signal_name TEXT PRIMARY KEY,
                correlation_coefficient REAL DEFAULT 0.0,
                p_value REAL DEFAULT 1.0,
                sample_size INTEGER DEFAULT 0,
                significance TEXT DEFAULT 'not_significant'
            );

            CREATE TABLE IF NOT EXISTS capability_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task TEXT NOT NULL,
                date_from TEXT NOT NULL,
                date_to TEXT NOT NULL,
                score_change REAL NOT NULL,
                type TEXT NOT NULL,
                contributing_factors TEXT DEFAULT '[]',
                severity TEXT DEFAULT 'low'
            );
        """)
        self._initialized = True

    async def update_timeline(self, date: str, recipes: List[Dict[str, Any]]) -> None:
        await self._init_schema()
        if not recipes:
            return

        total_score = sum(float(r.get("evaluation", {}).get("score", 0)) for r in recipes)
        avg_score = total_score / len(recipes) if recipes else 0

        memory_versions = set()
        prompt_versions = set()
        for r in recipes:
            if r.get("memory_version"):
                memory_versions.add(f"v{r['memory_version']}")
            if r.get("prompt_version"):
                prompt_versions.add(f"v{r['prompt_version']}")

        timeline_id = f"timeline-{date}"
        await self._db.execute(
            "INSERT OR REPLACE INTO intelligence_timeline VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                timeline_id, date, len(recipes), avg_score,
                avg_score, self._db.serialize_json(list(memory_versions)),
                self._db.serialize_json(list(prompt_versions)),
            ),
        )
        await self._db.commit()

    async def get_timeline(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        await self._init_schema()
        rows = await self._db.fetchall(
            "SELECT * FROM intelligence_timeline WHERE date >= ? AND date <= ? ORDER BY date ASC",
            (start_date, end_date),
        )
        for row in rows:
            row["memory_versions"] = self._db.deserialize_json(row.get("memory_versions"), default=[])
            row["prompt_versions"] = self._db.deserialize_json(row.get("prompt_versions"), default=[])
        return rows

    async def update_obsolescent_prompts(
        self, prompt_id: str, prompt_name: str, usage_count: int, avg_relevance: float, trend: str = "stable"
    ) -> None:
        await self._init_schema()
        await self._db.execute(
            "INSERT OR REPLACE INTO obsolescent_prompts VALUES (?, ?, ?, ?, ?, ?)",
            (prompt_id, prompt_name, usage_count, avg_relevance, trend, datetime.now().date().isoformat()),
        )
        await self._db.commit()

    async def get_obsolescent_prompts(self, lookback_days: int = 30) -> List[Dict[str, Any]]:
        await self._init_schema()
        return await self._db.fetchall(
            "SELECT * FROM obsolescent_prompts WHERE usage_count < ? ORDER BY avg_relevance ASC LIMIT 50",
            (lookback_days * 2,),
        )

    async def update_unused_memories(
        self, memory_id: str, title: str, usage_count: int, last_retrieved: Optional[str] = None
    ) -> None:
        await self._init_schema()
        await self._db.execute(
            "INSERT OR REPLACE INTO unused_memories VALUES (?, ?, ?, ?)",
            (memory_id, title, usage_count, last_retrieved or datetime.now().date().isoformat()),
        )
        await self._db.commit()

    async def get_unused_memories(self, lookback_days: int = 30) -> List[Dict[str, Any]]:
        await self._init_schema()
        cutoff = (datetime.now() - timedelta(days=lookback_days)).date().isoformat()
        return await self._db.fetchall(
            "SELECT * FROM unused_memories WHERE last_retrieved < ? OR last_retrieved IS NULL ORDER BY usage_count ASC LIMIT 50",
            (cutoff,),
        )

    async def update_signal_correlation(
        self, signal_name: str, correlation_coefficient: float, p_value: float, sample_size: int
    ) -> None:
        await self._init_schema()
        significance = "not_significant"
        if p_value < 0.05 and abs(correlation_coefficient) > 0.5:
            significance = "significant"
        elif p_value < 0.1 and abs(correlation_coefficient) > 0.3:
            significance = "marginal"

        await self._db.execute(
            "INSERT OR REPLACE INTO signal_correlations VALUES (?, ?, ?, ?, ?)",
            (signal_name, correlation_coefficient, p_value, sample_size, significance),
        )
        await self._db.commit()

    async def get_signal_correlations(self) -> List[Dict[str, Any]]:
        await self._init_schema()
        return await self._db.fetchall("SELECT * FROM signal_correlations")

    async def record_capability_change(
        self, task: str, date_from: str, date_to: str, score_change: float,
        change_type: str, factors: List[str], severity: str = "low"
    ) -> None:
        await self._init_schema()
        await self._db.execute(
            "INSERT INTO capability_changes (task, date_from, date_to, score_change, type, contributing_factors, severity) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (task, date_from, date_to, score_change, change_type, self._db.serialize_json(factors), severity),
        )
        await self._db.commit()

    async def get_capability_changes(self, lookback_days: int = 7) -> Dict[str, List[Dict[str, Any]]]:
        await self._init_schema()
        cutoff = (datetime.now() - timedelta(days=lookback_days)).date().isoformat()
        regressions = await self._db.fetchall(
            "SELECT * FROM capability_changes WHERE type='regression' AND date_to >= ? ORDER BY score_change ASC",
            (cutoff,),
        )
        improvements = await self._db.fetchall(
            "SELECT * FROM capability_changes WHERE type='improvement' AND date_to >= ? ORDER BY score_change DESC",
            (cutoff,),
        )
        for lst in (regressions, improvements):
            for row in lst:
                row["contributing_factors"] = self._db.deserialize_json(row.get("contributing_factors"), default=[])
        return {"regressions": regressions, "improvements": improvements}

    async def get_observatory_stats(self) -> Dict[str, Any]:
        await self._init_schema()
        counts = {}
        for name in ("intelligence_timeline", "obsolescent_prompts", "unused_memories", "signal_correlations"):
            row = await self._db.fetchone(f"SELECT COUNT(*) AS cnt FROM {name}")
            counts[name] = row["cnt"] if row else 0
        change_row = await self._db.fetchone("SELECT COUNT(*) AS cnt FROM capability_changes")
        counts["capability_changes"] = change_row["cnt"] if change_row else 0

        return {
            "timeline_entries": counts["intelligence_timeline"],
            "obsolescent_prompts": counts["obsolescent_prompts"],
            "unused_memories": counts["unused_memories"],
            "signal_correlations": counts["signal_correlations"],
            "capability_changes": counts["capability_changes"],
            "last_updated": datetime.now().isoformat(),
        }

    async def close(self) -> None:
        await self._db.close()
