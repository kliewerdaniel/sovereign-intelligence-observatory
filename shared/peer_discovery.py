"""LAN Peer Discovery for local network agent topology.

Uses UDP broadcast to discover neighboring Sovereign Intelligence
Observatory instances on the same subnet.  Optionally wraps Zeroconf
(Bonjour/mDNS) when the ``zeroconf`` package is installed.

Environment variables:
  DISCOVERY_PORT       int   Default 42069
  DISCOVERY_INTERVAL   int   Seconds between heartbeats (default 30)
  DISCOVERY_TIMEOUT    int   Seconds before a peer is considered stale (default 90)
  DISCOVERY_TTL        int   IP time-to-live for multicast (default 2)
"""

import asyncio
import json
import logging
import os
import socket
import struct
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Set, Callable, Awaitable

logger = logging.getLogger(__name__)

DISCOVERY_PORT = int(os.getenv("DISCOVERY_PORT", "42069"))
DISCOVERY_INTERVAL = int(os.getenv("DISCOVERY_INTERVAL", "30"))
DISCOVERY_TIMEOUT = int(os.getenv("DISCOVERY_TIMEOUT", "90"))
DISCOVERY_TTL = int(os.getenv("DISCOVERY_TTL", "2"))

# Broadcast / multicast group (site-local scope)
MULTICAST_GROUP = "239.255.42.69"
BROADCAST_PORT = DISCOVERY_PORT


@dataclass
class PeerInfo:
    agent_id: str
    host: str
    port: int
    service: str = "sovereign-observatory"
    last_seen: float = 0.0

    def is_stale(self, timeout: int = DISCOVERY_TIMEOUT) -> bool:
        return time.monotonic() - self.last_seen > timeout


class PeerDiscovery:
    """Broadcast peer presence on the LAN and maintain a peer table.

    Usage:
        pd = PeerDiscovery(agent_id="agent-alpha", service_port=8000)
        pd.on_peer_joined = lambda p: logger.info("New peer: %s", p.agent_id)
        await pd.start()
        # ...
        await pd.stop()
    """

    def __init__(
        self,
        agent_id: str,
        service_port: int,
        discovery_port: int = BROADCAST_PORT,
        interval_s: int = DISCOVERY_INTERVAL,
        timeout_s: int = DISCOVERY_TIMEOUT,
        ttl: int = DISCOVERY_TTL,
    ):
        self.agent_id = agent_id
        self.service_port = service_port
        self.discovery_port = discovery_port
        self.interval_s = interval_s
        self.timeout_s = timeout_s
        self.ttl = ttl

        self._peers: Dict[str, PeerInfo] = {}
        self._running = False
        self._sock: Optional[socket.socket] = None
        self._task: Optional[asyncio.Task] = None

        # Callbacks: async def callback(peer: PeerInfo) -> None
        self.on_peer_joined: Optional[Callable[[PeerInfo], Awaitable[None]]] = None
        self.on_peer_lost: Optional[Callable[[PeerInfo], Awaitable[None]]] = None

    # ── Lifecycle ────────────────────────────────────────────────────────────

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._sock = self._make_socket()
        self._task = asyncio.create_task(self._loop())
        logger.info(
            "PeerDiscovery started on port %d (agent=%s, interval=%ds)",
            self.discovery_port, self.agent_id, self.interval_s,
        )

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self._sock is not None:
            self._sock.close()
            self._sock = None
        self._peers.clear()
        logger.info("PeerDiscovery stopped")

    # ── Peer table ───────────────────────────────────────────────────────────

    @property
    def peers(self) -> Dict[str, PeerInfo]:
        now = time.monotonic()
        return {
            aid: info for aid, info in self._peers.items()
            if not info.is_stale(self.timeout_s)
        }

    @property
    def peer_count(self) -> int:
        return len(self.peers)

    # ── Internal ─────────────────────────────────────────────────────────────

    def _make_socket(self) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Allow loopback for single-machine testing.
        try:
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
        except Exception:
            pass

        # Join multicast group.
        try:
            mreq = struct.pack("4sl", socket.inet_aton(MULTICAST_GROUP), socket.INADDR_ANY)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        except Exception as exc:
            logger.debug("Could not join multicast group: %s", exc)

        # TTL for outbound multicast.
        try:
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, self.ttl)
        except Exception:
            pass

        sock.settimeout(1.0)
        try:
            sock.bind(("", self.discovery_port))
        except OSError as exc:
            logger.warning("PeerDiscovery bind failed on port %d: %s", self.discovery_port, exc)
        return sock

    def _build_announcement(self) -> bytes:
        return json.dumps({
            "agent_id": self.agent_id,
            "port": self.service_port,
            "service": "sovereign-observatory",
            "ts": time.time(),
        }).encode()

    async def _loop(self) -> None:
        loop = asyncio.get_running_loop()
        announcement = self._build_announcement()

        while self._running:
            try:
                # Send heartbeat via multicast.
                await loop.sock_sendto(
                    self._sock, announcement, (MULTICAST_GROUP, self.discovery_port)
                )

                # Receive announcements from peers.
                while True:
                    try:
                        data, addr = await loop.sock_recvfrom(self._sock, 2048)
                    except socket.timeout:
                        break
                    try:
                        msg = json.loads(data.decode().strip())
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        continue
                    peer_agent = msg.get("agent_id", "")
                    if peer_agent == self.agent_id:
                        continue  # skip self
                    now = time.monotonic()
                    was_new = peer_agent not in self._peers
                    self._peers[peer_agent] = PeerInfo(
                        agent_id=peer_agent,
                        host=addr[0],
                        port=int(msg.get("port", self.service_port)),
                        service=msg.get("service", "sovereign-observatory"),
                        last_seen=now,
                    )
                    if was_new and self.on_peer_joined is not None:
                        await self.on_peer_joined(self._peers[peer_agent])

                # Expire stale peers.
                stale = [aid for aid, info in self._peers.items() if info.is_stale(self.timeout_s)]
                for aid in stale:
                    expired = self._peers.pop(aid)
                    if self.on_peer_lost is not None:
                        await self.on_peer_lost(expired)

                await asyncio.sleep(self.interval_s)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("PeerDiscovery loop error: %s", exc)
                await asyncio.sleep(5)
