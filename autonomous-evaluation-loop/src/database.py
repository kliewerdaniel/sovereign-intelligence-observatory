"""Autonomous Evaluation Loop - Asynchronous Database Layer"""

import math
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from shared.async_db import AsyncDatabase
from .models import EvaluationSignal, EvaluationResult, SignalDriftReport, SignalType, SignalStatus


def _kolmogorov_smirnov_statistic(sample_a: List[float], sample_b: List[float]) -> float:
    """Two-sample Kolmogorov-Smirnov D statistic.

    Returns the maximum absolute difference between the empirical
    cumulative distribution functions of two samples (0.0 = identical,
    1.0 = completely separated).
    """
    if not sample_a or not sample_b:
        return 0.0
    combined = sorted(set(sample_a + sample_b))
    max_diff = 0.0
    for val in combined:
        cdf_a = sum(1 for x in sample_a if x <= val) / len(sample_a)
        cdf_b = sum(1 for x in sample_b if x <= val) / len(sample_b)
        max_diff = max(max_diff, abs(cdf_a - cdf_b))
    return max_diff


def _population_stability_index(expected: List[float], actual: List[float], n_bins: int = 10) -> float:
    """Population Stability Index (PSI).

    Compares the distribution of ``actual`` scores against ``expected``
    using equal-width binning.  PSI < 0.1 indicates no significant shift,
    0.1--0.25 moderate, > 0.25 large shift.
    """
    if not expected or not actual:
        return 0.0
    all_vals = expected + actual
    lo, hi = min(all_vals), max(all_vals)
    if hi - lo < 1e-9:
        return 0.0
    bin_width = (hi - lo) / n_bins

    def _bin_counts(data: List[float]) -> List[int]:
        counts = [0] * n_bins
        for v in data:
            idx = min(int((v - lo) / bin_width), n_bins - 1)
            counts[idx] += 1
        return counts

    exp_counts = _bin_counts(expected)
    act_counts = _bin_counts(actual)
    n_exp = len(expected)
    n_act = len(actual)

    psi = 0.0
    for i in range(n_bins):
        p_exp = (exp_counts[i] + 0.5) / (n_exp + 0.5 * n_bins)
        p_act = (act_counts[i] + 0.5) / (n_act + 0.5 * n_bins)
        psi += (p_act - p_exp) * math.log(p_act / p_exp)
    return psi


def _validate_evaluation_input(score: float, recent_scores: List[float]) -> bool:
    """Reject synthetic / degenerate scores that would create feedback loops.

    Returns ``True`` if the score appears valid, ``False`` if it looks
    synthetic (exact duplicates of recent scores, all identical, etc.).
    """
    if score < 0.0 or score > 1.0:
        return False
    if len(recent_scores) >= 3:
        if all(s == score for s in recent_scores[-3:]):
            return False
    return True


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

    async def detect_drift(self, signal_id: str, lookback_days: int = 30, ks_threshold: float = 0.3, psi_threshold: float = 0.25) -> Optional[SignalDriftReport]:
        """Detect distribution drift using KS test + PSI statistics.

        Parameters
        ----------
        signal_id:
            Which signal to evaluate.
        lookback_days:
            Window for "recent" scores.
        ks_threshold:
            Kolmogorov-Smirnov D above this indicates drift.
        psi_threshold:
            Population Stability Index above this indicates drift.
        """
        await self._init_schema()
        signal_row = await self._db.fetchone(
            "SELECT * FROM signals WHERE signal_id=?", (signal_id,)
        )
        if not signal_row:
            return None

        old_correlation = signal_row["correlation_coefficient"]
        cutoff = (datetime.now() - timedelta(days=lookback_days)).isoformat()
        mid_cutoff = (datetime.now() - timedelta(days=lookback_days * 2)).isoformat()

        recent_rows = await self._db.fetchall(
            "SELECT score FROM evaluation_results WHERE signal_id=? AND timestamp>=? ORDER BY timestamp ASC",
            (signal_id, cutoff),
        )
        historic_rows = await self._db.fetchall(
            "SELECT score FROM evaluation_results WHERE signal_id=? AND timestamp>=? AND timestamp<? ORDER BY timestamp ASC",
            (signal_id, mid_cutoff, cutoff),
        )

        if not recent_rows:
            return None

        recent_scores = [r["score"] for r in recent_rows]
        historic_scores = [r["score"] for r in historic_rows] if historic_rows else recent_scores

        ks_d = _kolmogorov_smirnov_statistic(historic_scores, recent_scores)
        psi = _population_stability_index(historic_scores, recent_scores)
        mean_shift = abs(sum(historic_scores) / len(historic_scores) - sum(recent_scores) / len(recent_scores)) if historic_scores else 0.0

        new_correlation = sum(recent_scores) / len(recent_scores)
        drift_detected = ks_d > ks_threshold or psi > psi_threshold
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
