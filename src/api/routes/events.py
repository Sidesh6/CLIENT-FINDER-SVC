"""
Real-time WebSockets and Server-Sent Events (SSE) route handlers.
Provides bi-directional live event streaming and broadcast endpoints.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from src.api.events import GLOBAL_EVENT_BROADCASTER, EventType, SystemEvent

router = APIRouter(prefix="/api", tags=["Real-Time Live Events & Streaming"])
logger = logging.getLogger("EventsRouter")


@router.websocket("/ws/events")
async def websocket_events_endpoint(websocket: WebSocket) -> None:
    """
    WebSocket endpoint streaming live discovery, scoring, and lifecycle events.
    """
    await GLOBAL_EVENT_BROADCASTER.connect_ws(websocket)
    try:
        # Send initial connection handshake confirmation
        initial_event = SystemEvent(
            event_type=EventType.PING,
            data={"status": "connected", "message": "Client Finder Live Event Stream Active"},
        )
        await websocket.send_text(initial_event.to_json())

        # Keep connection open and handle optional inbound client pings
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(
                    SystemEvent(event_type=EventType.PING, data={"pong": True}).to_json()
                )
    except WebSocketDisconnect:
        await GLOBAL_EVENT_BROADCASTER.disconnect_ws(websocket)
    except Exception as exc:
        logger.warning("WebSocket connection exception: %s", exc)
        await GLOBAL_EVENT_BROADCASTER.disconnect_ws(websocket)


@router.get("/events/stream")
async def sse_events_stream() -> StreamingResponse:
    """
    Server-Sent Events (SSE) fallback endpoint for environments without WebSocket support.
    """
    queue = await GLOBAL_EVENT_BROADCASTER.subscribe_sse()

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # Yield initial connection event
            yield 'event: PING\ndata: {"status": "connected"}\n\n'
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield event.to_sse_format()
                except TimeoutError:
                    # Keep-alive heartbeat comment
                    yield ": heartbeat\n\n"
        finally:
            await GLOBAL_EVENT_BROADCASTER.unsubscribe_sse(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/events/broadcast-test")
def broadcast_test_event(message: str = "Test real-time broadcast") -> dict[str, Any]:
    """
    Publish a test event to verify WebSocket and SSE client reception.
    """
    GLOBAL_EVENT_BROADCASTER.broadcast_sync(
        event_type=EventType.PING,
        data={"test": True, "message": message},
    )
    return {"status": "broadcast_dispatched", "message": message}
