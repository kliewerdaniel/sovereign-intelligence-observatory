"""Intelligence Observatory - Database Layer"""
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict


class ObservatoryDatabase:
    def __init__(self, db_path: str = "observatory.db"):
        self.db_path = db_path
        self._init()
    
    def _init(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS intelligence_timeline (
                    id TEXT PRIMARY KEY,
                    date TEXT NOT NULL,
                    recipe_count INTEGER DEFAULT 0,
                    avg_score REAL DEFAULT 0.0,
                    capability_index REAL DEFAULT 1.0,
                    memory_versions TEXT,
                    prompt_versions TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS obsolescent_prompts (
                    prompt_id TEXT PRIMARY KEY,
                    prompt_name TEXT NOT NULL,
                    usage_count INTEGER DEFAULT 0,
                    avg_relevance REAL DEFAULT 0.0,
                    trend TEXT DEFAULT 'stable',
                    last_used TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS unused_memories (
                    memory_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    usage_count INTEGER DEFAULT 0,
                    last_retrieved TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS signal_correlations (
                    signal_name TEXT PRIMARY KEY,
                    correlation_coefficient REAL DEFAULT 0.0,
                    p_value REAL DEFAULT 1.0,
                    sample_size INTEGER DEFAULT 0,
                    significance TEXT DEFAULT 'not_significant'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS capability_changes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task TEXT NOT NULL,
                    date_from TEXT NOT NULL,
                    date_to TEXT NOT NULL,
                    score_change REAL NOT NULL,
                    type TEXT NOT NULL,  -- 'regression' or 'improvement'
                    contributing_factors TEXT,
                    severity TEXT DEFAULT 'low'
                )
            """)
            conn.commit()
    
    def update_timeline(self, date: str, recipes: List[Dict[str, Any]]):
        """Update timeline for a specific date"""
        if not recipes:
            return
        
        total_score = sum(float(r.get('evaluation', {}).get('score', 0)) for r in recipes)
        avg_score = total_score / len(recipes) if recipes else 0
        
        memory_versions = set()
        prompt_versions = set()
        for r in recipes:
            if r.get('memory_version'):
                memory_versions.add(f"v{r['memory_version']}")
            if r.get('prompt_version'):
                prompt_versions.add(f"v{r['prompt_version']}")
        
        timeline_id = f"timeline-{date}"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO intelligence_timeline 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                timeline_id, date, len(recipes), avg_score,
                avg_score, str(list(memory_versions)), str(list(prompt_versions))
            ))
            conn.commit()
    
    def get_timeline(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Get intelligence timeline for a date range"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM intelligence_timeline 
                WHERE date >= ? AND date <= ?
                ORDER BY date ASC
            """, (start_date, end_date))
            return [dict(zip([d[0] for d in cursor.description], row)) for row in cursor.fetchall()]
    
    def update_obsolescent_prompts(self, prompt_id: str, prompt_name: str, usage_count: int, avg_relevance: float, trend: str = 'stable'):
        """Update obsolescent prompt data"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO obsolescent_prompts 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (prompt_id, prompt_name, usage_count, avg_relevance, trend, datetime.now().date().isoformat()))
            conn.commit()
    
    def get_obsolescent_prompts(self, lookback_days: int = 30) -> List[Dict[str, Any]]:
        """Get obsolescent prompts"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM obsolescent_prompts 
                WHERE usage_count < ? 
                ORDER BY avg_relevance ASC
                LIMIT 50
            """, (lookback_days * 2,))  # Simple heuristic
            return [dict(zip([d[0] for d in cursor.description], row)) for row in cursor.fetchall()]
    
    def update_unused_memories(self, memory_id: str, title: str, usage_count: int, last_retrieved: Optional[str] = None):
        """Update unused memory data"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO unused_memories 
                VALUES (?, ?, ?, ?)
            """, (memory_id, title, usage_count, last_retrieved or datetime.now().date().isoformat()))
            conn.commit()
    
    def get_unused_memories(self, lookback_days: int = 30) -> List[Dict[str, Any]]:
        """Get unused memories"""
        cutoff = (datetime.now() - timedelta(days=lookback_days)).date().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM unused_memories 
                WHERE last_retrieved < ? OR last_retrieved IS NULL
                ORDER BY usage_count ASC
                LIMIT 50
            """, (cutoff,))
            return [dict(zip([d[0] for d in cursor.description], row)) for row in cursor.fetchall()]
    
    def update_signal_correlation(self, signal_name: str, correlation_coefficient: float, p_value: float, sample_size: int):
        """Update signal correlation data"""
        significance = 'not_significant'
        if p_value < 0.05 and abs(correlation_coefficient) > 0.5:
            significance = 'significant'
        elif p_value < 0.1 and abs(correlation_coefficient) > 0.3:
            significance = 'marginal'
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO signal_correlations 
                VALUES (?, ?, ?, ?, ?)
            """, (signal_name, correlation_coefficient, p_value, sample_size, significance))
            conn.commit()
    
    def get_signal_correlations(self) -> List[Dict[str, Any]]:
        """Get signal correlations"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM signal_correlations")
            return [dict(zip([d[0] for d in cursor.description], row)) for row in cursor.fetchall()]
    
    def record_capability_change(self, task: str, date_from: str, date_to: str, score_change: float, change_type: str, factors: List[str], severity: str = 'low'):
        """Record capability regression or improvement"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO capability_changes (task, date_from, date_to, score_change, type, contributing_factors, severity)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (task, date_from, date_to, score_change, change_type, str(factors), severity))
            conn.commit()
    
    def get_capability_changes(self, lookback_days: int = 7) -> Dict[str, List[Dict[str, Any]]]:
        """Get recent capability regressions and improvements"""
        cutoff = (datetime.now() - timedelta(days=lookback_days)).date().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            regressions = conn.execute("""
                SELECT * FROM capability_changes 
                WHERE type='regression' AND date_to >= ?
                ORDER BY score_change ASC
            """, (cutoff,)).fetchall()
            
            improvements = conn.execute("""
                SELECT * FROM capability_changes 
                WHERE type='improvement' AND date_to >= ?
                ORDER BY score_change DESC
            """, (cutoff,)).fetchall()
            
            columns = [d[0] for d in conn.execute("SELECT * FROM capability_changes LIMIT 1").description]
            
            return {
                'regressions': [dict(zip(columns, r)) for r in regressions],
                'improvements': [dict(zip(columns, r)) for r in improvements]
            }
    
    def get_observatory_stats(self) -> Dict[str, Any]:
        """Get overall observatory statistics"""
        with sqlite3.connect(self.db_path) as conn:
            timeline_count = conn.execute("SELECT COUNT(*) FROM intelligence_timeline").fetchone()[0]
            prompt_count = conn.execute("SELECT COUNT(*) FROM obsolescent_prompts").fetchone()[0]
            memory_count = conn.execute("SELECT COUNT(*) FROM unused_memories").fetchone()[0]
            signal_count = conn.execute("SELECT COUNT(*) FROM signal_correlations").fetchone()[0]
            change_count = conn.execute("SELECT COUNT(*) FROM capability_changes").fetchone()[0]
            
            return {
                'timeline_entries': timeline_count,
                'obsolescent_prompts': prompt_count,
                'unused_memories': memory_count,
                'signal_correlations': signal_count,
                'capability_changes': change_count,
                'last_updated': datetime.now().isoformat()
            }
