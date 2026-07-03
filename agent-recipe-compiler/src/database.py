"""Agent Recipe Compiler - Asynchronous SQLite Database Layer"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from shared.async_db import AsyncDatabase


class RecipeDatabase:
    """Async SQLite store for agent recipes with FTS5 full-text search."""

    def __init__(self, db_path: str = ":memory:"):
        self._db = AsyncDatabase(db_path)
        self._initialized = False

    async def _init_schema(self) -> None:
        if self._initialized:
            return
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS recipes (
                recipe_id TEXT PRIMARY KEY,
                objective TEXT NOT NULL,
                model TEXT NOT NULL,
                prompt_version INTEGER NOT NULL,
                memory_version INTEGER NOT NULL,
                retrieved_docs TEXT NOT NULL DEFAULT '[]',
                reasoning_patterns TEXT NOT NULL DEFAULT '[]',
                evaluation TEXT NOT NULL DEFAULT '{}',
                outcome TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}'
            );
        """)
        await self._db.ensure_fts5_trigger(
            table="recipes",
            fts_table="recipes_fts",
            content_columns=["objective", "model", "outcome", "retrieved_docs", "reasoning_patterns"],
        )
        self._initialized = True

    async def store_recipe(self, recipe_data: Dict[str, Any]) -> str:
        await self._init_schema()
        await self._db.execute(
            """
            INSERT OR REPLACE INTO recipes (
                recipe_id, objective, model, prompt_version, memory_version,
                retrieved_docs, reasoning_patterns, evaluation, outcome,
                created_at, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                recipe_data["recipe_id"],
                recipe_data["objective"],
                recipe_data["model"],
                recipe_data["prompt_version"],
                recipe_data["memory_version"],
                self._db.serialize_json(recipe_data.get("retrieved_docs", [])),
                self._db.serialize_json(recipe_data.get("reasoning_patterns", [])),
                self._db.serialize_json(recipe_data.get("evaluation", {})),
                recipe_data.get("outcome", "pending"),
                recipe_data["created_at"],
                self._db.serialize_json(recipe_data.get("metadata", {})),
            ),
        )
        await self._db.commit()
        return recipe_data["recipe_id"]

    async def get_recipe(self, recipe_id: str) -> Optional[Dict[str, Any]]:
        await self._init_schema()
        row = await self._db.fetchone("SELECT * FROM recipes WHERE recipe_id = ?", (recipe_id,))
        if row is None:
            return None
        return self._deserialize_row(row)

    async def list_recipes(
        self,
        objective: Optional[str] = None,
        model: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        outcome: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        await self._init_schema()
        conditions: List[str] = []
        params: List[Any] = []

        if objective:
            conditions.append("objective LIKE ?")
            params.append(f"%{objective}%")
        if model:
            conditions.append("model = ?")
            params.append(model)
        if date_from:
            conditions.append("created_at >= ?")
            params.append(date_from)
        if date_to:
            conditions.append("created_at <= ?")
            params.append(date_to)
        if outcome:
            conditions.append("outcome = ?")
            params.append(outcome)

        where = " AND ".join(conditions) if conditions else "1=1"

        count_row = await self._db.fetchone(
            f"SELECT COUNT(*) as cnt FROM recipes WHERE {where}", tuple(params)
        )
        total = count_row["cnt"] if count_row else 0

        rows = await self._db.fetchall(
            f"SELECT * FROM recipes WHERE {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            tuple(params) + (limit, offset),
        )
        return [self._deserialize_row(r) for r in rows], total

    async def search_recipes(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        await self._init_schema()
        rows = await self._db.fetchall(
            """
            SELECT r.* FROM recipes_fts fts
            JOIN recipes r ON r.rowid = fts.rowid
            WHERE recipes_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (query, limit),
        )
        return [self._deserialize_row(r) for r in rows]

    async def get_recipe_count(self) -> int:
        await self._init_schema()
        row = await self._db.fetchone("SELECT COUNT(*) AS cnt FROM recipes")
        return row["cnt"] if row else 0

    async def get_recipe_stats(self) -> Dict[str, Any]:
        await self._init_schema()
        row = await self._db.fetchone(
            """
            SELECT
                COUNT(*) AS total,
                COUNT(CASE WHEN outcome = 'accepted' THEN 1 END) AS accepted,
                COUNT(CASE WHEN outcome = 'rejected' THEN 1 END) AS rejected,
                COUNT(DISTINCT model) AS unique_models,
                COUNT(DISTINCT objective) AS unique_objectives
            FROM recipes
            """
        )
        return dict(row) if row else {"total": 0, "accepted": 0, "rejected": 0, "unique_models": 0, "unique_objectives": 0}

    async def close(self) -> None:
        await self._db.close()

    def _deserialize_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        row["retrieved_docs"] = self._db.deserialize_json(row.get("retrieved_docs"), default=[])
        row["reasoning_patterns"] = self._db.deserialize_json(row.get("reasoning_patterns"), default=[])
        row["evaluation"] = self._db.deserialize_json(row.get("evaluation"), default={"score": 0.0, "reviewed_by": "none"})
        row["metadata"] = self._db.deserialize_json(row.get("metadata"), default={})
        return row
