"""Expert Signal Router - Database Layer"""
import sqlite3
from typing import List, Optional, Dict, Any
from datetime import datetime


class SignalDatabase:
    def __init__(self, db_path: str = "signals.db"):
        self.db_path = db_path
        self._init()
    
    def _init(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS evaluations (
                    id TEXT PRIMARY KEY,
                    recipe_id TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    decision TEXT NOT NULL,
                    feedback TEXT,
                    reviewed_by TEXT,
                    reviewed_at TEXT,
                    FOREIGN KEY (recipe_id) REFERENCES recipes(recipe_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS routing_config (
                    objective TEXT PRIMARY KEY,
                    cheap_threshold REAL DEFAULT 0.8,
                    expert_threshold REAL DEFAULT 0.5,
                    auto_approve_threshold REAL DEFAULT 0.95
                )
            """)
            conn.commit()
    
    def route_recipe(self, recipe_id: str, objective: str, confidence: float) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT cheap_threshold, expert_threshold, auto_approve_threshold FROM routing_config WHERE objective = ?",
                (objective,)
            ).fetchone()
            
            if not row:
                cheap, expert, auto_approve = 0.8, 0.5, 0.95
            else:
                cheap, expert, auto_approve = row[0], row[1], row[2]
            
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
            conn.execute(
                "INSERT INTO evaluations VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (eval_id, recipe_id, signal_type, confidence, decision, "", "", datetime.now().isoformat())
            )
            conn.commit()
            return {"evaluation_id": eval_id, "signal_type": signal_type, "decision": decision}
    
    def record_expert_review(self, evaluation_id: str, decision: str, feedback: str, reviewed_by: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE evaluations SET decision=?, feedback=?, reviewed_by=? WHERE id=?",
                (decision, feedback, reviewed_by, evaluation_id)
            )
            conn.commit()
    
    def get_pending_reviews(self) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM evaluations WHERE decision='pending_review' ORDER BY reviewed_at DESC"
            )
            return [dict(zip([d[0] for d in cursor.description], row)) for row in cursor.fetchall()]
    
    def get_signal_statistics(self) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT signal_type, COUNT(*), AVG(confidence)
                FROM evaluations GROUP BY signal_type
            """)
            return {
                "total": conn.execute("SELECT COUNT(*) FROM evaluations").fetchone()[0],
                "by_signal": [{"type": r[0], "count": r[1], "avg_confidence": r[2]} for r in cursor.fetchall()]
            }
