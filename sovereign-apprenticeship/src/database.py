"""Sovereign Apprenticeship Engine - Database Layer"""
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import sys
import os

try:
    from .models import AutonomyState, AutonomyLevel, AutonomyTransition, AutonomyBudget
except ImportError:
    sys.path.insert(0, os.path.dirname(__file__))
    from models import AutonomyState, AutonomyLevel, AutonomyTransition, AutonomyBudget


class ApprenticeshipDatabase:
    def __init__(self, db_path: str = "apprenticeship.db"):
        self.db_path = db_path
        self._init()
    
    def _init(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS autonomy_states (
                    agent_id TEXT PRIMARY KEY,
                    level TEXT NOT NULL,
                    supervision_ratio REAL NOT NULL,
                    autonomy_budget_remaining INTEGER NOT NULL,
                    total_actions INTEGER DEFAULT 0,
                    monitored_actions INTEGER DEFAULT 0,
                    autonomy_debt REAL DEFAULT 0.0,
                    last_updated TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS autonomy_transitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL,
                    from_level TEXT NOT NULL,
                    to_level TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    quality_threshold REAL NOT NULL,
                    transition_date TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS autonomy_budgets (
                    agent_id TEXT PRIMARY KEY,
                    daily_budget INTEGER DEFAULT 100,
                    used_today INTEGER DEFAULT 0,
                    reset_date TEXT NOT NULL,
                    warnings_issued INTEGER DEFAULT 0
                )
            """)
            conn.commit()
    
    def get_or_create_state(self, agent_id: str) -> AutonomyState:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM autonomy_states WHERE agent_id=?",
                (agent_id,)
            ).fetchone()
            
            if row:
                return AutonomyState(
                    agent_id=row[0],
                    level=AutonomyLevel(row[1]),
                    supervision_ratio=row[2],
                    autonomy_budget_remaining=row[3],
                    total_actions=row[4],
                    monitored_actions=row[5],
                    autonomy_debt=row[6],
                    last_updated=datetime.fromisoformat(row[7])
                )
            else:
                state = AutonomyState(
                    agent_id=agent_id,
                    level=AutonomyLevel.FULLY_SUPERVISED,
                    supervision_ratio=1.0,
                    autonomy_budget_remaining=0
                )
                self.save_state(state)
                return state
    
    def save_state(self, state: AutonomyState):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO autonomy_states VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (state.agent_id, state.level.value, state.supervision_ratio,
                 state.autonomy_budget_remaining, state.total_actions,
                 state.monitored_actions, state.autonomy_debt, state.last_updated.isoformat())
            )
            conn.commit()
    
    def record_action(self, agent_id: str, monitored: bool, quality_score: float):
        state = self.get_or_create_state(agent_id)
        state.total_actions += 1
        if monitored:
            state.monitored_actions += 1
        
        if not monitored and quality_score < 0.7:
            state.autonomy_debt += (1.0 - quality_score)
        
        # Check for autonomy debt threshold
        if state.autonomy_debt > 2.0:
            self.demote_agent(agent_id, "autonomy_debt_exceeded", "Quality too low for current autonomy level")
        
        self.save_state(state)
    
    def promote_agent(self, agent_id: str, new_level: AutonomyLevel, reason: str, quality_threshold: float):
        state = self.get_or_create_state(agent_id)
        from_level = state.level
        
        transition = AutonomyTransition(
            agent_id=agent_id,
            from_level=from_level,
            to_level=new_level,
            reason=reason,
            quality_threshold=quality_threshold
        )
        
        state.level = new_level
        state.supervision_ratio = 1.0 - new_level.value.replace("fully_", "").count("_") * 0.25
        state.autonomy_budget_remaining = self._calculate_budget(new_level)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO autonomy_transitions (agent_id, from_level, to_level, reason, quality_threshold, transition_date) VALUES (?, ?, ?, ?, ?, ?)",
                (agent_id, from_level.value, new_level.value, reason, quality_threshold, datetime.now().isoformat())
            )
        self.save_state(state)
    
    def demote_agent(self, agent_id: str, reason: str, quality_threshold: float):
        state = self.get_or_create_state(agent_id)
        from_level = state.level
        
        # Find the next lower autonomy level
        levels = list(AutonomyLevel)
        current_idx = levels.index(from_level)
        if current_idx < len(levels) - 1:
            new_level = levels[current_idx + 1]
        else:
            return  # Already at lowest level
        
        self.promote_agent(agent_id, new_level, reason, quality_threshold)
    
    def _calculate_budget(self, level: AutonomyLevel) -> int:
        budgets = {
            AutonomyLevel.FULLY_SUPERVISED: 0,
            AutonomyLevel.APPROVE_DANGEROUS: 10,
            AutonomyLevel.APPROVE_NOVEL: 50,
            AutonomyLevel.APPROVE_UNCERTAIN: 100,
            AutonomyLevel.FULLY_AUTONOMOUS: 500
        }
        return budgets.get(level, 0)
    
    def get_agent_state(self, agent_id: str) -> Optional[AutonomyState]:
        try:
            return self.get_or_create_state(agent_id)
        except:
            return None
    
    def get_transition_history(self, agent_id: str) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM autonomy_transitions WHERE agent_id=? ORDER BY transition_date DESC",
                (agent_id,)
            )
            return [dict(zip([d[0] for d in cursor.description], row)) for row in cursor.fetchall()]
