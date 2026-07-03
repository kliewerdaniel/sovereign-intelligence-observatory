"""WebSocket telemetry loop with delta-encoded broadcasts.

Pushes only the changed fields between cycles (delta encoding) to
reduce bandwidth.  A full snapshot is sent every FULL_CYCLE_INTERVAL
cycles (default every 6th = every 30 s) so that late-joining clients
or clients that missed a delta can re-sync.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Set, Dict, Any, Optional

from fastapi import WebSocket, WebSocketDisconnect

from .database import ObservatoryDatabase

logger = logging.getLogger(__name__)

RECONNECT_DELAY_S = 1.0
PUSH_INTERVAL_S = 5.0
FULL_CYCLE_INTERVAL = 6  # Every 6 cycles = 30 s, send full snapshot


class TelemetryManager:
    """Manages WebSocket connections with delta-encoded broadcasts."""

    def __init__(self):
        self._connections: Set[WebSocket] = set()
        self._broadcast_task: Optional[asyncio.Task] = None
        self._previous_payload: Optional[Dict[str, Any]] = None
        self._cycle_count: int = 0
        self._send_full: bool = True  # Send full on first broadcast

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)
        logger.debug("Telemetry client connected (%d total)", len(self._connections))
        if self._broadcast_task is None or self._broadcast_task.done():
            self._broadcast_task = asyncio.create_task(self._broadcast_loop())

    async def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)
        logger.debug("Telemetry client disconnected (%d remaining)", len(self._connections))

    def _compute_delta(
        self, previous: Dict[str, Any], current: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Return only the top-level keys that changed between payloads."""
        delta: Dict[str, Any] = {}
        for key in current:
            if key not in previous:
                delta[key] = current[key]
            elif previous[key] != current[key]:
                delta[key] = current[key]
        for key in previous:
            if key not in current:
                delta[key] = None
        return delta

    async def _broadcast_loop(self) -> None:
        while self._connections:
            try:
                db = ObservatoryDatabase()
                payload = await self._collect_payload(db)
                await db.close()

                self._cycle_count += 1
                send_full = self._send_full or (
                    self._cycle_count % FULL_CYCLE_INTERVAL == 0
                )

                message: Dict[str, Any]
                if send_full or self._previous_payload is None:
                    message = {"full": payload, "ts": payload["ts"]}
                    self._send_full = False
                else:
                    delta = self._compute_delta(self._previous_payload, payload)
                    message = {"delta": delta, "ts": payload["ts"]}

                self._previous_payload = payload

                dead = set()
                for ws in self._connections.copy():
                    try:
                        await ws.send_json(message)
                    except Exception:
                        dead.add(ws)
                for ws in dead:
                    await self.disconnect(ws)

                await asyncio.sleep(PUSH_INTERVAL_S)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Telemetry broadcast error: %s", exc)
                await asyncio.sleep(RECONNECT_DELAY_S)

    async def _collect_payload(self, db: ObservatoryDatabase) -> Dict[str, Any]:
        """Gather timeline stats, drift alerts, and obsolescence signals."""
        stats = await db.get_observatory_stats()
        timeline = await db.get_timeline(
            (datetime.now() - timedelta(days=30)).date().isoformat(),
            datetime.now().date().isoformat(),
        )
        obsolescent = await db.get_obsolescent_prompts(lookback_days=30)
        changes = await db.get_capability_changes(lookback_days=7)

        drift_alerts = []
        for c in changes.get("regressions", []):
            drift_alerts.append({
                "type": "regression",
                "task": c.get("task", "unknown"),
                "score_change": c.get("score_change", 0.0),
                "severity": c.get("severity", "low"),
            })

        return {
            "ts": datetime.now().isoformat(),
            "stats": stats,
            "timeline": timeline[-30:] if timeline else [],
            "obsolescent_count": len(obsolescent),
            "drift_alerts": drift_alerts[:10],
        }

    async def shutdown(self) -> None:
        if self._broadcast_task is not None and not self._broadcast_task.done():
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass
        for ws in self._connections.copy():
            try:
                await ws.close()
            except Exception:
                pass
        self._connections.clear()


telemetry_manager = TelemetryManager()
