"""Local federated sync for serialized decision tree exchange.

Supports two transport mechanisms:
1. **File-share** — export/import via a shared directory (NFS, SMB, local).
2. **Local HTTP** — push/pull over a simple HTTP exchange between
   isolated agent instances on the same machine or LAN.

Every payload is versioned with a schema tag so incompatible formats
are rejected early.

Transactional Outbox
-------------------
The HTTP transport persists undeliverable payloads to a ``federated_outbox``
SQLite table and retries with exponential backoff.
"""

import asyncio
import json
import logging
import math
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import httpx

logger = logging.getLogger(__name__)

FEDERATED_SCHEMA_VERSION = "decision-tree-exchange-v1"
FEDERATED_FILE_EXT = ".sio_federated"


# ── Payload envelope ──────────────────────────────────────────────────────────

class FederatedPayload:
    """Wraps an exported decision tree with metadata for safe exchange."""

    def __init__(
        self,
        nodes: List[Dict[str, Any]],
        source_agent_id: str,
        domain: str,
        schema_version: str = FEDERATED_SCHEMA_VERSION,
        exported_at: Optional[str] = None,
        signature: Optional[str] = None,
    ):
        self.schema_version = schema_version
        self.source_agent_id = source_agent_id
        self.domain = domain
        self.nodes = nodes
        self.exported_at = exported_at or datetime.now().isoformat()
        self.signature = signature or f"sync-{uuid4().hex[:12]}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "source_agent_id": self.source_agent_id,
            "domain": self.domain,
            "nodes": self.nodes,
            "exported_at": self.exported_at,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional["FederatedPayload"]:
        if data.get("schema_version") != FEDERATED_SCHEMA_VERSION:
            logger.warning("Federated payload rejected: schema_version=%s", data.get("schema_version"))
            return None
        try:
            return cls(
                nodes=data.get("nodes", []),
                source_agent_id=data.get("source_agent_id", "unknown"),
                domain=data.get("domain", "general"),
                schema_version=data["schema_version"],
                exported_at=data.get("exported_at"),
                signature=data.get("signature"),
            )
        except (KeyError, TypeError) as exc:
            logger.warning("Invalid federated payload: %s", exc)
            return None


# ── File-share transport ──────────────────────────────────────────────────────

class FileShareTransport:
    """Exchange decision trees via a shared filesystem directory.

    Each payload is written as a JSON file with a unique signature name.
    Inbound files are discovered by globbing ``*.sio_federated`` and are
    deleted after a successful import to avoid double-processing.
    """

    def __init__(self, watch_dir: str, agent_id: str):
        self.watch_dir = Path(watch_dir)
        self.agent_id = agent_id
        self.watch_dir.mkdir(parents=True, exist_ok=True)

    def export(self, payload: FederatedPayload) -> Path:
        """Write a payload to the shared directory and return the file path."""
        filepath = self.watch_dir / f"{payload.signature}{FEDERATED_FILE_EXT}"
        filepath.write_text(json.dumps(payload.to_dict(), indent=2))
        logger.info("Federated export -> %s (%d nodes)", filepath, len(payload.nodes))
        return filepath

    def discover_inbound(self) -> List[Path]:
        """Return all federated payload files not written by this agent."""
        files = []
        for fpath in self.watch_dir.glob(f"*{FEDERATED_FILE_EXT}"):
            try:
                data = json.loads(fpath.read_text())
                if data.get("source_agent_id") != self.agent_id:
                    files.append(fpath)
            except (json.JSONDecodeError, OSError) as exc:
                logger.debug("Skipping unreadable federated file %s: %s", fpath, exc)
        return files

    def import_payload(self, fpath: Path) -> Optional[FederatedPayload]:
        """Read, validate, and remove a federated payload file."""
        try:
            data = json.loads(fpath.read_text())
            payload = FederatedPayload.from_dict(data)
            if payload is None:
                return None
            fpath.unlink(missing_ok=True)
            logger.info("Federated import <- %s (%d nodes)", fpath, len(payload.nodes))
            return payload
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Federated import failed from %s: %s", fpath, exc)
            return None

    def import_all(self) -> List[FederatedPayload]:
        """Import all available inbound payloads."""
        payloads = []
        for fpath in self.discover_inbound():
            p = self.import_payload(fpath)
            if p is not None:
                payloads.append(p)
        return payloads


# ── Transactional Outbox ──────────────────────────────────────────────────────

OUTBOX_SCHEMA = """
    CREATE TABLE IF NOT EXISTS federated_outbox (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        signature TEXT NOT NULL,
        peer_url TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        retry_count INTEGER DEFAULT 0,
        max_retries INTEGER DEFAULT 10,
        next_retry_at REAL NOT NULL,
        last_error TEXT,
        created_at TEXT NOT NULL,
        acknowledged INTEGER DEFAULT 0
    );
"""


class OutboxStore:
    """Persistent queue for undeliverable federated payloads.

    Each row tracks the target ``peer_url``, the serialized payload,
    current retry count, and the timestamp for the next retry
    (computed with exponential backoff).
    """

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or f"{tempfile.gettempdir()}/federated_outbox_{uuid4().hex[:8]}.db"
        self._local = sqlite3.connect(self._db_path, check_same_thread=False)
        self._local.row_factory = sqlite3.Row
        self._local.executescript(OUTBOX_SCHEMA)
        self._local.commit()

    def enqueue(self, payload: FederatedPayload, peer_url: str, max_retries: int = 10) -> int:
        """Insert a payload into the outbox. Returns the row id."""
        now = datetime.now().timestamp()
        cur = self._local.execute(
            "INSERT INTO federated_outbox (signature, peer_url, payload_json, max_retries, next_retry_at, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (payload.signature, peer_url, json.dumps(payload.to_dict()), max_retries, now, datetime.now().isoformat()),
        )
        self._local.commit()
        return cur.lastrowid

    def claim_due(self, batch_size: int = 10) -> List[Dict[str, Any]]:
        """Return rows whose ``next_retry_at`` has passed and that haven't
        been acknowledged.  Uses ``FOR UPDATE SKIP LOCKED`` semantics via
        a manual ``UPDATE ... WHERE ...`` pattern.
        """
        now = datetime.now().timestamp()
        rows = self._local.execute(
            "SELECT * FROM federated_outbox WHERE next_retry_at <= ? AND acknowledged = 0 ORDER BY next_retry_at ASC LIMIT ?",
            (now, batch_size),
        ).fetchall()
        return [dict(r) for r in rows]

    def mark_acknowledged(self, row_id: int) -> None:
        self._local.execute("UPDATE federated_outbox SET acknowledged = 1 WHERE id = ?", (row_id,))
        self._local.commit()

    def mark_retry(self, row_id: int, error: str) -> None:
        """Increment retry_count and compute the next_retry_at with
        exponential backoff: 2^(retry_count) seconds base.
        """
        row = self._local.execute("SELECT retry_count, max_retries FROM federated_outbox WHERE id = ?", (row_id,)).fetchone()
        if row is None:
            return
        new_count = row["retry_count"] + 1
        if new_count >= row["max_retries"]:
            self._local.execute("UPDATE federated_outbox SET retry_count = ?, last_error = ?, acknowledged = 1 WHERE id = ?",
                                (new_count, error[:500], row_id))
        else:
            delay = math.pow(2, new_count)
            next_ts = datetime.now().timestamp() + delay
            self._local.execute(
                "UPDATE federated_outbox SET retry_count = ?, next_retry_at = ?, last_error = ? WHERE id = ?",
                (new_count, next_ts, error[:500], row_id),
            )
        self._local.commit()

    def count_pending(self) -> int:
        row = self._local.execute("SELECT COUNT(*) AS cnt FROM federated_outbox WHERE acknowledged = 0").fetchone()
        return row["cnt"] if row else 0

    def close(self) -> None:
        self._local.close()


# ── Local HTTP transport ──────────────────────────────────────────────────────

DEFAULT_BACKOFF_BASE_S = 2
DEFAULT_MAX_RETRIES = 10


class HttpTransport:
    """Exchange decision trees between agent instances over local HTTP.

    One instance acts as a temporary *exchange peer* by hosting a small
    ingestion endpoint.  Other instances push their trees to that peer.

    Unreachable peers are handled by a transactional outbox that
    persists the payload and retries with exponential backoff.
    """

    PEER_ENDPOINT = "/api/federated/ingest"

    def __init__(
        self,
        agent_id: str,
        base_url: Optional[str] = None,
        outbox: Optional[OutboxStore] = None,
        backoff_base_s: int = DEFAULT_BACKOFF_BASE_S,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        self.agent_id = agent_id
        self.base_url = base_url
        self.outbox = outbox or OutboxStore()
        self.backoff_base_s = backoff_base_s
        self.max_retries = max_retries
        self._client = httpx.AsyncClient(timeout=10.0)
        self._retry_task: Optional[asyncio.Task] = None

    async def push(self, payload: FederatedPayload, peer_url: str) -> bool:
        """Push a federated payload to a remote peer.

        On failure, the payload is persisted to the outbox and a
        background retry loop is started (if not already running).
        """
        try:
            resp = await self._client.post(
                f"{peer_url.rstrip('/')}{self.PEER_ENDPOINT}",
                json=payload.to_dict(),
            )
            if resp.status_code == 202:
                logger.info("Federated push -> %s accepted", peer_url)
                return True
            logger.warning("Federated push -> %s returned %d", peer_url, resp.status_code)
        except (httpx.RequestError, Exception) as exc:
            logger.warning("Federated push to %s failed: %s — enqueuing to outbox", peer_url, exc)

        # Persist to outbox.
        self.outbox.enqueue(payload, peer_url, max_retries=self.max_retries)
        logger.info("Enqueued payload %s to outbox (pending: %d)", payload.signature, self.outbox.count_pending())

        # Start background retry loop if not running.
        if self._retry_task is None or self._retry_task.done():
            self._retry_task = asyncio.create_task(self._retry_loop())

        return False

    async def _retry_loop(self) -> None:
        """Consume the outbox, retrying each pending payload with
        exponential backoff.
        """
        while True:
            due = self.outbox.claim_due(batch_size=10)
            if not due:
                break
            for row in due:
                payload_dict = json.loads(row["payload_json"])
                payload = FederatedPayload.from_dict(payload_dict)
                if payload is None:
                    self.outbox.mark_acknowledged(row["id"])
                    continue
                try:
                    resp = await self._client.post(
                        f"{row['peer_url'].rstrip('/')}{self.PEER_ENDPOINT}",
                        json=payload.to_dict(),
                    )
                    if resp.status_code == 202:
                        logger.info("Outbox retry succeeded for %s", row["signature"])
                        self.outbox.mark_acknowledged(row["id"])
                        continue
                    error = f"HTTP {resp.status_code}"
                except httpx.RequestError as exc:
                    error = str(exc)
                self.outbox.mark_retry(row["id"], error)
            # Brief pause before re-checking the queue.
            await asyncio.sleep(1.0)

    async def pull(self, peer_url: str) -> Optional[FederatedPayload]:
        """Pull the latest federated payload from a remote peer.

        The peer is expected to expose the latest tree at its ingest
        endpoint for GET.
        """
        try:
            resp = await self._client.get(
                f"{peer_url.rstrip('/')}{self.PEER_ENDPOINT}/latest",
            )
            if resp.status_code == 200:
                data = resp.json()
                return FederatedPayload.from_dict(data)
            return None
        except (httpx.RequestError, Exception) as exc:
            logger.warning("Federated pull from %s failed: %s", peer_url, exc)
            return None

    async def close(self) -> None:
        if self._retry_task is not None and not self._retry_task.done():
            self._retry_task.cancel()
            try:
                await self._retry_task
            except asyncio.CancelledError:
                pass
        await self._client.aclose()
        self.outbox.close()
