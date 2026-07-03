"""Local federated sync for serialized decision tree exchange.

Supports two transport mechanisms:
1. **File-share** — export/import via a shared directory (NFS, SMB, local).
2. **Local HTTP** — push/pull over a simple HTTP exchange between
   isolated agent instances on the same machine or LAN.

Every payload is versioned with a schema tag so incompatible formats
are rejected early.
"""

import json
import logging
import os
import time
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


# ── Local HTTP transport ──────────────────────────────────────────────────────

class HttpTransport:
    """Exchange decision trees between agent instances over local HTTP.

    One instance acts as a temporary *exchange peer* by hosting a small
    ingestion endpoint.  Other instances push their trees to that peer.
    """

    PEER_ENDPOINT = "/api/federated/ingest"

    def __init__(self, agent_id: str, base_url: Optional[str] = None):
        self.agent_id = agent_id
        self.base_url = base_url
        self._client = httpx.AsyncClient(timeout=10.0)

    async def push(self, payload: FederatedPayload, peer_url: str) -> bool:
        """Push a federated payload to a remote peer."""
        try:
            resp = await self._client.post(
                f"{peer_url.rstrip('/')}{self.PEER_ENDPOINT}",
                json=payload.to_dict(),
            )
            if resp.status_code == 202:
                logger.info("Federated push -> %s accepted", peer_url)
                return True
            logger.warning("Federated push -> %s returned %d", peer_url, resp.status_code)
            return False
        except (httpx.RequestError, Exception) as exc:
            logger.warning("Federated push to %s failed: %s", peer_url, exc)
            return False

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
        await self._client.aclose()
