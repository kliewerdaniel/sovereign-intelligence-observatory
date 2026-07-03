"""Asynchronous SQLite base with FTS5 support and JSON handling"""

import asyncio
import json
import logging
import aiosqlite
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class AsyncDatabase:
    """Async SQLite database with FTS5 and JSON helper methods."""

    def __init__(self, db_path: str = ":memory:", busy_timeout: int = 5000):
        self.db_path = db_path
        self.busy_timeout = busy_timeout
        self._conn: Optional[aiosqlite.Connection] = None
        self._maintenance_task: Optional[asyncio.Task] = None

    async def connect(self) -> aiosqlite.Connection:
        if self._conn is None:
            self._conn = await aiosqlite.connect(self.db_path, timeout=self.busy_timeout / 1000)
            self._conn.row_factory = aiosqlite.Row
            await self._conn.execute("PRAGMA journal_mode=WAL")
            await self._conn.execute("PRAGMA synchronous=NORMAL")
            await self._conn.execute(f"PRAGMA busy_timeout={self.busy_timeout}")
            await self._conn.execute("PRAGMA foreign_keys=ON")
            await self._conn.execute("PRAGMA cache_size=-8000")
        return self._conn

    async def close(self) -> None:
        if self._maintenance_task is not None:
            self._maintenance_task.cancel()
            try:
                await self._maintenance_task
            except asyncio.CancelledError:
                pass
            self._maintenance_task = None
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

    async def run_maintenance(self, vacuum_threshold_mb: int = 100) -> None:
        """Non-blocking housekeeping: PRAGMA optimize + conditional VACUUM.

        ``PRAGMA optimize`` is a no-op if nothing needs optimisation.
        ``VACUUM`` is only run when the database file on disk exceeds
        *vacuum_threshold_mb* (ignored for in-memory databases).
        """
        if self.db_path == ":memory:":
            return
        conn = await self.connect()

        # PRAGMA optimize — safe to call concurrently with readers.
        await conn.execute("PRAGMA optimize")

        # Conditional VACUUM based on file size.
        try:
            db_path = Path(self.db_path)
            if db_path.exists() and db_path.stat().st_size > vacuum_threshold_mb * 1024 * 1024:
                await conn.execute("VACUUM")
                logger.info("VACUUM completed on %s (was > %d MB)", self.db_path, vacuum_threshold_mb)
        except OSError as exc:
            logger.debug("Skipping VACUUM file-size check: %s", exc)

    async def start_periodic_maintenance(
        self, interval_s: int = 3600, vacuum_threshold_mb: int = 100,
    ) -> asyncio.Task:
        """Launch a background task that runs maintenance every *interval_s* seconds.

        The task checks a sentinel flag before each run so that a prior
        run still in progress is skipped.  Call ``cancel()`` on the
        returned task to stop the loop.
        """
        self._maintenance_task = asyncio.create_task(
            self._maintenance_loop(interval_s, vacuum_threshold_mb)
        )
        return self._maintenance_task

    async def _maintenance_loop(self, interval_s: int, vacuum_threshold_mb: int) -> None:
        running = False
        while True:
            await asyncio.sleep(interval_s)
            if running:
                logger.debug("Skipping maintenance — previous run still in progress")
                continue
            running = True
            try:
                await self.run_maintenance(vacuum_threshold_mb)
            except Exception as exc:
                logger.warning("Periodic maintenance error: %s", exc)
            finally:
                running = False

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
