"""Tacit Judgment Extractor - Asynchronous Database Layer"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import uuid4

from shared.async_db import AsyncDatabase
from .models import DecisionNode, SessionState, PatternAnalysis, DecisionTreeExport


class TacitJudgmentDatabase:
    def __init__(self, db_path: str = ":memory:"):
        self._db = AsyncDatabase(db_path)
        self._initialized = False

    async def _init_schema(self) -> None:
        if self._initialized:
            return
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS expert_sessions (
                session_id TEXT PRIMARY KEY,
                expert_id TEXT NOT NULL,
                domain TEXT NOT NULL,
                session_text TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'recording',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS session_corrections (
                correction_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                original_text TEXT NOT NULL,
                corrected_text TEXT NOT NULL,
                rationale TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES expert_sessions(session_id)
            );

            CREATE TABLE IF NOT EXISTS decision_nodes (
                node_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                parent_id TEXT,
                condition TEXT NOT NULL DEFAULT '',
                action TEXT NOT NULL DEFAULT '',
                confidence REAL NOT NULL DEFAULT 0.0,
                rationale TEXT NOT NULL DEFAULT '',
                children TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES expert_sessions(session_id)
            );

            CREATE TABLE IF NOT EXISTS pattern_analyses (
                pattern_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                pattern_type TEXT NOT NULL,
                confidence REAL NOT NULL DEFAULT 0.0,
                description TEXT NOT NULL DEFAULT '',
                extracted_rules TEXT NOT NULL DEFAULT '[]',
                suggested_node TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES expert_sessions(session_id)
            );

            CREATE TABLE IF NOT EXISTS decision_tree_exports (
                tree_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                domain TEXT NOT NULL,
                expert_id TEXT NOT NULL,
                export_data TEXT NOT NULL,
                schema_version TEXT NOT NULL DEFAULT '1.0.0',
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES expert_sessions(session_id)
            );
        """)
        await self._db.ensure_fts5_trigger(
            table="expert_sessions",
            fts_table="expert_sessions_fts",
            content_columns=["domain", "session_text"],
        )
        self._initialized = True

    async def create_session(
        self, session_id: str, expert_id: str, domain: str, session_text: str
    ) -> str:
        await self._init_schema()
        now = datetime.now().isoformat()
        await self._db.execute(
            "INSERT INTO expert_sessions (session_id, expert_id, domain, session_text, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (session_id, expert_id, domain, session_text, SessionState.RECORDING.value, now, now),
        )
        await self._db.commit()
        return session_id

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        await self._init_schema()
        row = await self._db.fetchone(
            "SELECT * FROM expert_sessions WHERE session_id = ?", (session_id,)
        )
        if row is None:
            return None
        row["corrections"] = await self._db.fetchall(
            "SELECT * FROM session_corrections WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        )
        tree_rows = await self._db.fetchall(
            "SELECT * FROM decision_nodes WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        )
        for tr in tree_rows:
            tr["children"] = self._db.deserialize_json(tr.get("children"), default=[])
        row["decision_tree"] = tree_rows
        return row

    async def list_sessions(
        self, expert_id: Optional[str] = None, domain: Optional[str] = None,
        status: Optional[str] = None, limit: int = 50, offset: int = 0,
    ) -> List[Dict[str, Any]]:
        await self._init_schema()
        conditions = []
        params = []
        if expert_id:
            conditions.append("expert_id = ?")
            params.append(expert_id)
        if domain:
            conditions.append("domain = ?")
            params.append(domain)
        if status:
            conditions.append("status = ?")
            params.append(status)

        where = " AND ".join(conditions) if conditions else "1=1"
        return await self._db.fetchall(
            f"SELECT * FROM expert_sessions WHERE {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            tuple(params) + (limit, offset),
        )

    async def add_correction(
        self, session_id: str, original_text: str, corrected_text: str, rationale: str = ""
    ) -> str:
        await self._init_schema()
        correction_id = f"corr-{uuid4().hex[:12]}"
        now = datetime.now().isoformat()
        await self._db.execute(
            "INSERT INTO session_corrections VALUES (?, ?, ?, ?, ?, ?)",
            (correction_id, session_id, original_text, corrected_text, rationale, now),
        )
        await self._db.commit()
        return correction_id

    async def add_decision_node(self, session_id: str, node: DecisionNode) -> str:
        await self._init_schema()
        now = datetime.now().isoformat()
        await self._db.execute(
            "INSERT INTO decision_nodes (node_id, session_id, parent_id, condition, action, confidence, rationale, children, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (node.node_id, session_id, node.parent_id, node.condition, node.action,
             node.confidence, node.rationale, self._db.serialize_json(node.children), now),
        )
        await self._db.commit()
        return node.node_id

    async def add_pattern_analysis(self, session_id: str, analysis: PatternAnalysis) -> str:
        await self._init_schema()
        now = datetime.now().isoformat()
        await self._db.execute(
            "INSERT INTO pattern_analyses VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (analysis.pattern_id, session_id, analysis.pattern_type, analysis.confidence,
             analysis.description, self._db.serialize_json(analysis.extracted_rules),
             self._db.serialize_json(analysis.suggested_decision_node) if analysis.suggested_decision_node else None,
             now),
        )
        await self._db.commit()
        return analysis.pattern_id

    async def export_decision_tree(self, export: DecisionTreeExport) -> str:
        await self._init_schema()
        now = datetime.now().isoformat()
        await self._db.execute(
            "INSERT INTO decision_tree_exports (tree_id, session_id, domain, expert_id, export_data, schema_version, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (export.tree_id, export.session_id, export.domain, export.expert_id,
             self._db.serialize_json([n.model_dump() for n in export.nodes]),
             export.schema_version, now),
        )
        await self._db.commit()
        return export.tree_id

    async def get_tree_export(self, tree_id: str) -> Optional[Dict[str, Any]]:
        await self._init_schema()
        row = await self._db.fetchone(
            "SELECT * FROM decision_tree_exports WHERE tree_id = ?", (tree_id,)
        )
        if row is None:
            return None
        row["export_data"] = self._db.deserialize_json(row.get("export_data"), default=[])
        return row

    async def update_session_status(self, session_id: str, status: str) -> None:
        await self._init_schema()
        await self._db.execute(
            "UPDATE expert_sessions SET status=?, updated_at=? WHERE session_id=?",
            (status, datetime.now().isoformat(), session_id),
        )
        await self._db.commit()

    async def close(self) -> None:
        await self._db.close()
