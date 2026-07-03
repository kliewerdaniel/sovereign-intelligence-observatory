"""WebSocket telemetry loop for real-time observability.

Pushes timeline metrics and capability drift alerts to connected
front-end consumers without polling.
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


class TelemetryManager:
    """Manages WebSocket connections and broadcasts observability telemetry."""

    def __init__(self):
        self._connections: Set[WebSocket] = set()
        self._broadcast_task: Optional[asyncio.Task] = None

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)
        logger.debug("Telemetry client connected (%d total)", len(self._connections))
        # Start the broadcast loop when the first client connects
        if self._broadcast_task is None or self._broadcast_task.done():
            self._broadcast_task = asyncio.create_task(self._broadcast_loop())

    async def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)
        logger.debug("Telemetry client disconnected (%d remaining)", len(self._connections))

    async def _broadcast_loop(self) -> None:
        while self._connections:
            try:
                db = ObservatoryDatabase()
                payload = await self._collect_payload(db)
                await db.close()

                dead = set()
                for ws in self._connections.copy():
                    try:
                        await ws.send_json(payload)
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
