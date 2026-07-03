"""Asynchronous SQLite base with FTS5 support and JSON handling"""

import json
import aiosqlite
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple


class AsyncDatabase:
    """Async SQLite database with FTS5 and JSON helper methods."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self) -> aiosqlite.Connection:
        if self._conn is None:
            self._conn = await aiosqlite.connect(self.db_path)
            self._conn.row_factory = aiosqlite.Row
            await self._conn.execute("PRAGMA journal_mode=WAL")
            await self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def execute(self, sql: str, params: tuple = ()) -> aiosqlite.Cursor:
        conn = await self.connect()
        return await conn.execute(sql, params)

    async def executemany(self, sql: str, params: List[tuple]) -> aiosqlite.Cursor:
        conn = await self.connect()
        return await conn.executemany(sql, params)

    async def executescript(self, script: str) -> None:
        conn = await self.connect()
        await conn.executescript(script)

    async def fetchone(self, sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        conn = await self.connect()
        cursor = await conn.execute(sql, params)
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    async def fetchall(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        conn = await self.connect()
        cursor = await conn.execute(sql, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def commit(self) -> None:
        conn = await self.connect()
        await conn.commit()

    @staticmethod
    def serialize_json(value: Any) -> str:
        return json.dumps(value, default=str)

    @staticmethod
    def deserialize_json(value: Optional[str], default=None) -> Any:
        if value is None:
            return default if default is not None else {}
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return default if default is not None else {}

    async def ensure_fts5_trigger(
        self,
        table: str,
        fts_table: str,
        content_columns: List[str],
    ) -> None:
        """Create FTS5 virtual table and sync triggers for a given table."""
        col_list = ", ".join(content_columns)
        col_list_cs = ", ".join(f"new.{c}" for c in content_columns)
        col_list_os = ", ".join(f"old.{c}" for c in content_columns)

        await self.executescript(f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS {fts_table} USING fts5(
                {col_list},
                content='{table}',
                content_rowid='rowid'
            );

            CREATE TRIGGER IF NOT EXISTS {fts_table}_ai AFTER INSERT ON {table} BEGIN
                INSERT INTO {fts_table}(rowid, {col_list})
                VALUES (new.rowid, {col_list_cs});
            END;

            CREATE TRIGGER IF NOT EXISTS {fts_table}_ad AFTER DELETE ON {table} BEGIN
                INSERT INTO {fts_table}({fts_table}, rowid, {col_list})
                VALUES ('delete', old.rowid, {col_list_os});
            END;

            CREATE TRIGGER IF NOT EXISTS {fts_table}_au AFTER UPDATE ON {table} BEGIN
                INSERT INTO {fts_table}({fts_table}, rowid, {col_list})
                VALUES ('delete', old.rowid, {col_list_os});
                INSERT INTO {fts_table}(rowid, {col_list})
                VALUES (new.rowid, {col_list_cs});
            END;
        """)
        await self.commit()
