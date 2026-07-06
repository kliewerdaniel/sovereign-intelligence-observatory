"""Sovereign Apprenticeship Engine - Asynchronous Database Layer"""

import os
from typing import List, Dict, AsyncIterator, Optional, Any
from datetime import datetime

from shared.async_db import AsyncDatabase
from .models import AutonomyState, AutonomyLevel, AutonomyTransition

OUTBOX_CIRCUIT_BREAKER_LIMIT = int(os.getenv("OUTBOX_CIRCUIT_BREAKER_LIMIT", "50"))


class ApprenticeshipDatabase:
    def __init__(self, db_path: str = ":memory:", outbox=None):
        self._db = AsyncDatabase(db_path)
        self._outbox = outbox  # Optional OutboxStore for circuit breaker
        self._initialized = False

    async def _init_schema(self) -> None:
        if self._initialized:
            return
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS autonomy_states (
                agent_id TEXT PRIMARY KEY,
                level TEXT NOT NULL,
                supervision_ratio REAL NOT NULL,
                autonomy_budget_remaining INTEGER NOT NULL,
                total_actions INTEGER DEFAULT 0,
                monitored_actions INTEGER DEFAULT 0,
                autonomy_debt REAL DEFAULT 0.0,
                last_updated TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS autonomy_transitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                from_level TEXT NOT NULL,
                to_level TEXT NOT NULL,
                reason TEXT NOT NULL,
                quality_threshold REAL NOT NULL,
                transition_date TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS autonomy_budgets (
                agent_id TEXT PRIMARY KEY,
                daily_budget INTEGER DEFAULT 100,
                used_today INTEGER DEFAULT 0,
                reset_date TEXT NOT NULL,
                warnings_issued INTEGER DEFAULT 0
            );
        """)
        self._initialized = True

    async def get_or_create_state(self, agent_id: str) -> AutonomyState:
        await self._init_schema()
        row = await self._db.fetchone(
            "SELECT * FROM autonomy_states WHERE agent_id=?", (agent_id,)
        )
        if row:
            return AutonomyState(
                agent_id=row["agent_id"],
                level=AutonomyLevel(row["level"]),
                supervision_ratio=row["supervision_ratio"],
                autonomy_budget_remaining=row["autonomy_budget_remaining"],
                total_actions=row["total_actions"],
                monitored_actions=row["monitored_actions"],
                autonomy_debt=row["autonomy_debt"],
                last_updated=datetime.fromisoformat(row["last_updated"]),
            )
        else:
            state = AutonomyState(
                agent_id=agent_id,
                level=AutonomyLevel.FULLY_SUPERVISED,
                supervision_ratio=1.0,
                autonomy_budget_remaining=0,
            )
            await self._save_state(state)
            return state

    async def _ensure_budget_row(self, agent_id: str) -> Dict[str, Any]:
        await self._init_schema()
        row = await self._db.fetchone(
            "SELECT * FROM autonomy_budgets WHERE agent_id=?", (agent_id,)
        )
        today = datetime.now().date().isoformat()
        if row:
            if row["reset_date"] < today:
                await self._db.execute(
                    "UPDATE autonomy_budgets SET used_today=0, reset_date=?, warnings_issued=0 WHERE agent_id=?",
                    (today, agent_id),
                )
                await self._db.commit()
                row = await self._db.fetchone(
                    "SELECT * FROM autonomy_budgets WHERE agent_id=?", (agent_id,)
                )
            return row
        else:
            await self._db.execute(
                "INSERT INTO autonomy_budgets (agent_id, daily_budget, used_today, reset_date, warnings_issued) VALUES (?, 100, 0, ?, 0)",
                (agent_id, today),
            )
            await self._db.commit()
            return {"agent_id": agent_id, "daily_budget": 100, "used_today": 0, "reset_date": today, "warnings_issued": 0}

    def _compute_action_cost(self, monitored: bool, level: AutonomyLevel) -> float:
        base_costs = {
            AutonomyLevel.FULLY_SUPERVISED: 1.0,
            AutonomyLevel.APPROVE_DANGEROUS: 0.8,
            AutonomyLevel.APPROVE_NOVEL: 0.5,
            AutonomyLevel.APPROVE_UNCERTAIN: 0.3,
            AutonomyLevel.FULLY_AUTONOMOUS: 0.1,
        }
        cost = base_costs.get(level, 1.0)
        if monitored:
            cost *= 1.5
        return round(cost, 4)

    async def _save_state(self, state: AutonomyState) -> None:
        await self._db.execute(
            "INSERT OR REPLACE INTO autonomy_states VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                state.agent_id, state.level.value, state.supervision_ratio,
                state.autonomy_budget_remaining, state.total_actions,
                state.monitored_actions, state.autonomy_debt,
                state.last_updated.isoformat(),
            ),
        )
        await self._db.commit()

    async def record_action(
        self, agent_id: str, monitored: bool, quality_score: float,
    ) -> Dict[str, Any]:
        await self._init_schema()

        # Check outbox circuit breaker.
        circuit_breaked = False
        outbox_pending = 0
        if self._outbox is not None:
            outbox_pending = self._outbox.count_pending()
            if outbox_pending >= OUTBOX_CIRCUIT_BREAKER_LIMIT:
                circuit_breaked = True
                state = await self.get_or_create_state(agent_id)
                return {
                    "action_recorded": False,
                    "circuit_breaked": True,
                    "outbox_pending": outbox_pending,
                    "circuit_breaker_limit": OUTBOX_CIRCUIT_BREAKER_LIMIT,
                    "current_level": state.level.value,
                    "autonomy_budget_remaining": state.autonomy_budget_remaining,
                    "autonomy_debt": state.autonomy_debt,
                    "action_cost": 0.0,
                    "budget_used_today": 0,
                    "budget_daily_limit": 100,
                    "budget_exceeded": False,
                }

        state = await self.get_or_create_state(agent_id)
        state.total_actions += 1
        if monitored:
            state.monitored_actions += 1

        action_cost = self._compute_action_cost(monitored, state.level)
        budget = await self._ensure_budget_row(agent_id)
        new_used = budget["used_today"] + 1
        budget_exceeded = new_used > budget["daily_budget"]

        if not monitored and quality_score < 0.7:
            state.autonomy_debt += (1.0 - quality_score)

        if state.autonomy_debt > 2.0:
            await self._demote_agent(agent_id, "autonomy_debt_exceeded", "Quality too low for current autonomy level")
            state = await self.get_or_create_state(agent_id)

        await self._db.execute(
            "UPDATE autonomy_budgets SET used_today=? WHERE agent_id=?",
            (new_used, agent_id),
        )
        await self._save_state(state)

        return {
            "action_recorded": True,
            "circuit_breaked": False,
            "action_cost": action_cost,
            "budget_used_today": new_used,
            "budget_daily_limit": budget["daily_budget"],
            "budget_exceeded": budget_exceeded,
        }

    async def promote_agent(self, agent_id: str, new_level: AutonomyLevel, reason: str, quality_threshold: float) -> None:
        await self._init_schema()
        state = await self.get_or_create_state(agent_id)
        from_level = state.level

        transition = AutonomyTransition(
            agent_id=agent_id,
            from_level=from_level,
            to_level=new_level,
            reason=reason,
            quality_threshold=quality_threshold,
        )

        state.level = new_level
        state.supervision_ratio = self._calculate_supervision_ratio(new_level)
        state.autonomy_budget_remaining = self._calculate_budget(new_level)

        await self._save_transition(agent_id, from_level, new_level, reason, quality_threshold)
        await self._save_state(state)

    async def _demote_agent(self, agent_id: str, reason: str, quality_threshold: float) -> None:
        state = await self.get_or_create_state(agent_id)
        from_level = state.level
        levels = list(AutonomyLevel)
        current_idx = levels.index(from_level)
        if current_idx > 0:
            new_level = levels[current_idx - 1]
            await self._save_transition(agent_id, from_level, new_level, reason, quality_threshold)
            state.level = new_level
            state.supervision_ratio = min(1.0, state.supervision_ratio + 0.2)
            state.autonomy_debt = 0.0
            state.autonomy_budget_remaining = self._calculate_budget(new_level)
            await self._save_state(state)

    async def _save_transition(self, agent_id: str, from_level: AutonomyLevel, to_level: AutonomyLevel, reason: str, quality_threshold: float) -> None:
        await self._db.execute(
            "INSERT INTO autonomy_transitions (agent_id, from_level, to_level, reason, quality_threshold, transition_date) VALUES (?, ?, ?, ?, ?, ?)",
            (agent_id, from_level.value, to_level.value, reason, quality_threshold, datetime.now().isoformat()),
        )

    def _calculate_supervision_ratio(self, level: AutonomyLevel) -> float:
        ratios = {
            AutonomyLevel.FULLY_SUPERVISED: 1.0,
            AutonomyLevel.APPROVE_DANGEROUS: 0.75,
            AutonomyLevel.APPROVE_NOVEL: 0.5,
            AutonomyLevel.APPROVE_UNCERTAIN: 0.25,
            AutonomyLevel.FULLY_AUTONOMOUS: 0.05,
        }
        return ratios.get(level, 1.0)

    def _calculate_budget(self, level: AutonomyLevel) -> int:
        budgets = {
            AutonomyLevel.FULLY_SUPERVISED: 0,
            AutonomyLevel.APPROVE_DANGEROUS: 10,
            AutonomyLevel.APPROVE_NOVEL: 50,
            AutonomyLevel.APPROVE_UNCERTAIN: 100,
            AutonomyLevel.FULLY_AUTONOMOUS: 500,
        }
        return budgets.get(level, 0)

    async def get_agent_state(self, agent_id: str) -> Optional[AutonomyState]:
        try:
            return await self.get_or_create_state(agent_id)
        except Exception:
            return None

    async def get_transition_history(self, agent_id: str) -> List[Dict[str, Any]]:
        await self._init_schema()
        return await self._db.fetchall(
            "SELECT * FROM autonomy_transitions WHERE agent_id=? ORDER BY transition_date DESC",
            (agent_id,),
        )

    async def close(self) -> None:
        await self._db.close()
