"""Autonomous Evaluation Loop - Asynchronous Database Layer"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from shared.async_db import AsyncDatabase
from .models import EvaluationSignal, EvaluationResult, SignalDriftReport, SignalType, SignalStatus


class EvaluationDatabase:
    def __init__(self, db_path: str = ":memory:"):
        self._db = AsyncDatabase(db_path)
        self._initialized = False

    async def _init_schema(self) -> None:
        if self._initialized:
            return
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS signals (
                signal_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                threshold REAL NOT NULL,
                status TEXT DEFAULT 'active',
                correlation_coefficient REAL DEFAULT 0.0,
                p_value REAL DEFAULT 1.0,
                last_updated TEXT
            );

            CREATE TABLE IF NOT EXISTS evaluation_results (
                id TEXT PRIMARY KEY,
                recipe_id TEXT NOT NULL,
                signal_id TEXT NOT NULL,
                score REAL NOT NULL,
                passed INTEGER NOT NULL,
                timestamp TEXT,
                FOREIGN KEY (signal_id) REFERENCES signals(signal_id)
            );
        """)
        self._initialized = True

    async def create_signal(self, signal: EvaluationSignal) -> str:
        await self._init_schema()
        await self._db.execute(
            "INSERT INTO signals VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                signal.signal_id, signal.name, signal.signal_type.value,
                signal.threshold, signal.status.value, signal.correlation_coefficient,
                signal.p_value, signal.last_updated.isoformat(),
            ),
        )
        await self._db.commit()
        return signal.signal_id

    async def run_evaluation(self, recipe_id: str, signal: EvaluationSignal, score: float) -> EvaluationResult:
        await self._init_schema()
        result_id = f"result-{recipe_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        passed = score >= signal.threshold

        await self._db.execute(
            "INSERT INTO evaluation_results (id, recipe_id, signal_id, score, passed, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (result_id, recipe_id, signal.signal_id, score, int(passed), datetime.now().isoformat()),
        )
        await self._db.commit()

        return EvaluationResult(
            recipe_id=recipe_id,
            signal_id=signal.signal_id,
            score=score,
            passed=passed,
        )

    async def detect_drift(self, signal_id: str, lookback_days: int = 30) -> Optional[SignalDriftReport]:
        await self._init_schema()
        signal_row = await self._db.fetchone(
            "SELECT * FROM signals WHERE signal_id=?", (signal_id,)
        )
        if not signal_row:
            return None

        old_correlation = signal_row["correlation_coefficient"]
        cutoff = (datetime.now() - timedelta(days=lookback_days)).isoformat()

        row = await self._db.fetchone(
            "SELECT AVG(score) AS avg_score, COUNT(*) AS cnt FROM evaluation_results WHERE signal_id=? AND timestamp>=?",
            (signal_id, cutoff),
        )

        if row and row["cnt"] and row["cnt"] > 0:
            new_correlation = row["avg_score"]
            drift = abs(old_correlation - new_correlation)
            drift_detected = drift > 0.2
            status = "drifting" if drift_detected else "active"
            action = "review_required" if drift_detected else "continue_monitoring"

            await self._db.execute(
                "UPDATE signals SET status=?, correlation_coefficient=?, last_updated=? WHERE signal_id=?",
                (status, new_correlation, datetime.now().isoformat(), signal_id),
            )
            await self._db.commit()

            return SignalDriftReport(
                signal_id=signal_id,
                old_correlation=old_correlation,
                new_correlation=new_correlation,
                drift_detected=drift_detected,
                recommended_action=action,
            )

        return None

    async def get_signals(self) -> List[Dict[str, Any]]:
        await self._init_schema()
        return await self._db.fetchall("SELECT * FROM signals")

    async def get_signal(self, signal_id: str) -> Optional[Dict[str, Any]]:
        await self._init_schema()
        return await self._db.fetchone("SELECT * FROM signals WHERE signal_id=?", (signal_id,))

    async def get_evaluation_stats(self) -> Dict[str, Any]:
        await self._init_schema()
        total_row = await self._db.fetchone("SELECT COUNT(*) AS cnt FROM evaluation_results")
        total = total_row["cnt"] if total_row else 0
        passed_row = await self._db.fetchone("SELECT COUNT(*) AS cnt FROM evaluation_results WHERE passed=1")
        passed = passed_row["cnt"] if passed_row else 0
        return {"total": total, "passed": passed, "pass_rate": passed / total if total > 0 else 0.0}

    async def close(self) -> None:
        await self._db.close()
