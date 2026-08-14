"""
Real-time Event Broadcasting Subsystem for WebSockets and Server-Sent Events (SSE).
Coordinates asynchronous dispatch of pipeline telemetry, new opportunities, and status changes.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger("EventBroadcaster")


class EventType(str, Enum):
    """Event classifications supported across the real-time event bus."""

    NEW_OPPORTUNITY = "NEW_OPPORTUNITY"
    OPPORTUNITY_SCORED = "OPPORTUNITY_SCORED"
    CYCLE_COMPLETED = "CYCLE_COMPLETED"
    CIRCUIT_TRIPPED = "CIRCUIT_TRIPPED"
    APPLICATION_UPDATED = "APPLICATION_UPDATED"
    COLLECTOR_STATUS_CHANGED = "COLLECTOR_STATUS_CHANGED"
    PING = "PING"


@dataclass
class SystemEvent:
    """Structure of an outbound real-time event message."""

    event_type: EventType
    data: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_json(self) -> str:
        """Serialize event to JSON string."""
        return json.dumps(
            {
                "event_type": self.event_type.value,
                "data": self.data,
                "timestamp": self.timestamp,
            }
        )

    def to_sse_format(self) -> str:
        """Format event for Server-Sent Events stream."""
        return f"event: {self.event_type.value}\ndata: {json.dumps(self.data)}\n\n"


class EventBroadcaster:
    """
    Central event broadcaster managing active WebSockets and SSE listener queues.
    Thread-safe to allow background workers and sync coordinators to emit events.
    """

    def __init__(self) -> None:
        self._active_sockets: list[WebSocket] = []
        self._sse_subscribers: list[asyncio.Queue[SystemEvent]] = []
        self._lock = asyncio.Lock()
        self._main_loop: asyncio.AbstractEventLoop | None = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Register the primary asyncio event loop for threadsafe cross-thread dispatch."""
        self._main_loop = loop

    async def connect_ws(self, websocket: WebSocket) -> None:
        """Register an active client WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self._active_sockets.append(websocket)
        logger.info("Client connected via WebSocket. Active count: %d", len(self._active_sockets))

    async def disconnect_ws(self, websocket: WebSocket) -> None:
        """Remove a closed client WebSocket connection."""
        async with self._lock:
            if websocket in self._active_sockets:
                self._active_sockets.remove(websocket)
        logger.info(
            "Client disconnected from WebSocket. Active count: %d", len(self._active_sockets)
        )

    async def subscribe_sse(self) -> asyncio.Queue[SystemEvent]:
        """Subscribe an SSE streaming consumer."""
        queue: asyncio.Queue[SystemEvent] = asyncio.Queue(maxsize=100)
        async with self._lock:
            self._sse_subscribers.append(queue)
        logger.info("SSE client subscribed. Active SSE count: %d", len(self._sse_subscribers))
        return queue

    async def unsubscribe_sse(self, queue: asyncio.Queue[SystemEvent]) -> None:
        """Unsubscribe an SSE consumer."""
        async with self._lock:
            if queue in self._sse_subscribers:
                self._sse_subscribers.remove(queue)
        logger.info("SSE client unsubscribed. Active SSE count: %d", len(self._sse_subscribers))

    async def broadcast(self, event: SystemEvent) -> None:
        """Asynchronously publish an event to all connected WebSockets and SSE queues."""
        msg = event.to_json()
        dead_sockets: list[WebSocket] = []

        async with self._lock:
            # 1. Dispatch to WebSockets
            for ws in self._active_sockets:
                try:
                    await ws.send_text(msg)
                except Exception:
                    dead_sockets.append(ws)

            for dead in dead_sockets:
                if dead in self._active_sockets:
                    self._active_sockets.remove(dead)

            # 2. Dispatch to SSE queues
            for q in self._sse_subscribers:
                try:
                    q.put_nowait(event)
                except asyncio.QueueFull:
                    pass

    def broadcast_sync(self, event_type: EventType, data: dict[str, Any]) -> None:
        """
        Thread-safe synchronous bridge for background jobs, schedulers, and coordinator cycles.
        """
        event = SystemEvent(event_type=event_type, data=data)
        if self._main_loop and self._main_loop.is_running():
            asyncio.run_coroutine_threadsafe(self.broadcast(event), self._main_loop)
        else:
            try:
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    loop.create_task(self.broadcast(event))
            except RuntimeError:
                pass


# Global singleton instance
GLOBAL_EVENT_BROADCASTER = EventBroadcaster()
