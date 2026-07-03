"""Autonomous Evaluation Loop - Database Layer"""
import sqlite3
from typing import List, Dict, Any
from datetime import datetime, timedelta

try:
    from .models import EvaluationSignal, EvaluationResult, SignalDriftReport, SignalType, SignalStatus
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    from models import EvaluationSignal, EvaluationResult, SignalDriftReport, SignalType, SignalStatus


class EvaluationDatabase:
    def __init__(self, db_path: str = "evaluations.db"):
        self.db_path = db_path
        self._init()
    
    def _init(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    signal_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    threshold REAL NOT NULL,
                    status TEXT DEFAULT 'active',
                    correlation_coefficient REAL DEFAULT 0.0,
                    p_value REAL DEFAULT 1.0,
                    last_updated TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS evaluation_results (
                    id TEXT PRIMARY KEY,
                    recipe_id TEXT NOT NULL,
                    signal_id TEXT NOT NULL,
                    score REAL NOT NULL,
                    passed INTEGER NOT NULL,
                    timestamp TEXT,
                    FOREIGN KEY (signal_id) REFERENCES signals(signal_id)
                )
            """)
            conn.commit()
    
    def create_signal(self, signal: EvaluationSignal) -> str:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO signals VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (signal.signal_id, signal.name, signal.signal_type.value, 
                 signal.threshold, signal.status.value, signal.correlation_coefficient,
                 signal.p_value, signal.last_updated.isoformat())
            )
            conn.commit()
            return signal.signal_id
    
    def run_evaluation(self, recipe_id: str, signal: EvaluationSignal, score: float) -> EvaluationResult:
        result_id = f"result-{recipe_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        passed = score >= signal.threshold
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO evaluation_results (id, recipe_id, signal_id, score, passed, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (result_id, recipe_id, signal.signal_id, score, int(passed), datetime.now().isoformat())
            )
            conn.commit()
        
        return EvaluationResult(
            recipe_id=recipe_id,
            signal_id=signal.signal_id,
            score=score,
            passed=passed
        )
    
    def detect_drift(self, signal_id: str, lookback_days: int = 30) -> SignalDriftReport:
        with sqlite3.connect(self.db_path) as conn:
            # Get current correlation
            signal = conn.execute("SELECT * FROM signals WHERE signal_id=?", (signal_id,)).fetchone()
            if not signal:
                return None
            
            old_correlation = signal[5]
            
            # Calculate new correlation from recent results
            cutoff = (datetime.now() - timedelta(days=lookback_days)).isoformat()
            cursor = conn.execute(
                "SELECT AVG(score), COUNT(*) FROM evaluation_results WHERE signal_id=? AND timestamp>=?",
                (signal_id, cutoff)
            )
            row = cursor.fetchone()
            
            if row and row[1] and row[1] > 0:
                new_correlation = row[0]
                drift = abs(old_correlation - new_correlation)
                drift_detected = drift > 0.2
                
                status = "drifting" if drift_detected else "active"
                action = "review_required" if drift_detected else "continue_monitoring"
                
                # Update signal
                conn.execute(
                    "UPDATE signals SET status=?, correlation_coefficient=?, last_updated=? WHERE signal_id=?",
                    (status, new_correlation, datetime.now().isoformat(), signal_id)
                )
                conn.commit()
                
                return SignalDriftReport(
                    signal_id=signal_id,
                    old_correlation=old_correlation,
                    new_correlation=new_correlation,
                    drift_detected=drift_detected,
                    recommended_action=action
                )
        
        return None
    
    def get_signals(self) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM signals")
            return [dict(zip([d[0] for d in cursor.description], row)) for row in cursor.fetchall()]
    
    def get_evaluation_stats(self) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM evaluation_results").fetchone()[0]
            passed = conn.execute("SELECT COUNT(*) FROM evaluation_results WHERE passed=1").fetchone()[0]
            return {"total": total, "passed": passed, "pass_rate": passed/total if total > 0 else 0}
