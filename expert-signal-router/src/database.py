"""Expert Signal Router - Asynchronous Database Layer"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from shared.async_db import AsyncDatabase


class SignalDatabase:
    def __init__(self, db_path: str = ":memory:"):
        self._db = AsyncDatabase(db_path)
        self._initialized = False

    async def _init_schema(self) -> None:
        if self._initialized:
            return
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS evaluations (
                id TEXT PRIMARY KEY,
                recipe_id TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                decision TEXT NOT NULL,
                threshold_used REAL NOT NULL DEFAULT 0.0,
                feedback TEXT NOT NULL DEFAULT '',
                reviewed_by TEXT NOT NULL DEFAULT '',
                reviewed_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS routing_config (
                objective TEXT PRIMARY KEY,
                cheap_threshold REAL DEFAULT 0.8,
                expert_threshold REAL DEFAULT 0.5,
                auto_approve_threshold REAL DEFAULT 0.95
            );
        """)
        self._initialized = True

    async def route_recipe(self, recipe_id: str, objective: str, confidence: float) -> Dict[str, Any]:
        await self._init_schema()

        config = await self._db.fetchone(
            "SELECT cheap_threshold, expert_threshold, auto_approve_threshold FROM routing_config WHERE objective = ?",
            (objective,),
        )

        if config:
            cheap, expert, auto_approve = config["cheap_threshold"], config["expert_threshold"], config["auto_approve_threshold"]
        else:
            cheap, expert, auto_approve = 0.8, 0.5, 0.95

        if confidence >= auto_approve:
            signal_type = "auto_accepted"
            decision = "accepted"
        elif confidence >= cheap:
            signal_type = "cheap"
            decision = "accepted"
        else:
            signal_type = "expert"
            decision = "pending_review"

        eval_id = f"eval-{recipe_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        await self._db.execute(
            "INSERT INTO evaluations (id, recipe_id, signal_type, confidence, decision, threshold_used, feedback, reviewed_by, reviewed_at) VALUES (?, ?, ?, ?, ?, ?, '', '', ?)",
            (eval_id, recipe_id, signal_type, confidence, decision, auto_approve if confidence >= auto_approve else (cheap if confidence >= cheap else expert), datetime.now().isoformat()),
        )
        await self._db.commit()

        return {
            "evaluation_id": eval_id,
            "signal_type": signal_type,
            "decision": decision,
            "confidence": confidence,
            "threshold_used": auto_approve if confidence >= auto_approve else (cheap if confidence >= cheap else expert),
        }

    async def record_expert_review(self, evaluation_id: str, decision: str, feedback: str, reviewed_by: str) -> None:
        await self._init_schema()
        await self._db.execute(
            "UPDATE evaluations SET decision=?, feedback=?, reviewed_by=? WHERE id=?",
            (decision, feedback, reviewed_by, evaluation_id),
        )
        await self._db.commit()

    async def get_pending_reviews(self) -> List[Dict[str, Any]]:
        await self._init_schema()
        return await self._db.fetchall(
            "SELECT * FROM evaluations WHERE decision='pending_review' ORDER BY reviewed_at DESC"
        )

    async def get_signal_statistics(self) -> Dict[str, Any]:
        await self._init_schema()
        total_row = await self._db.fetchone("SELECT COUNT(*) AS cnt FROM evaluations")
        total = total_row["cnt"] if total_row else 0

        by_signal = await self._db.fetchall("""
            SELECT signal_type, COUNT(*) AS count, AVG(confidence) AS avg_confidence
            FROM evaluations GROUP BY signal_type
        """)

        return {
            "total": total,
            "by_signal": [
                {"type": r["signal_type"], "count": r["count"], "avg_confidence": r["avg_confidence"]}
                for r in by_signal
            ],
        }

    async def set_routing_config(
        self,
        objective: str,
        cheap_threshold: float = 0.8,
        expert_threshold: float = 0.5,
        auto_approve_threshold: float = 0.95,
    ) -> None:
        await self._init_schema()
        await self._db.execute(
            "INSERT OR REPLACE INTO routing_config VALUES (?, ?, ?, ?)",
            (objective, cheap_threshold, expert_threshold, auto_approve_threshold),
        )
        await self._db.commit()

    async def close(self) -> None:
        await self._db.close()
