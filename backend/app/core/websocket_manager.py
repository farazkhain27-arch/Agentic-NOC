"""WebSocket connection manager — broadcasts alarm events to all connected dashboard clients."""
import json
from typing import Set
from fastapi import WebSocket
import structlog

log = structlog.get_logger()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        log.info("ws_connect", total=len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        log.info("ws_disconnect", total=len(self.active_connections))

    async def broadcast(self, message: dict):
        if not self.active_connections:
            return
        data = json.dumps(message, default=str)
        dead = set()
        for ws in self.active_connections:
            try:
                await ws.send_text(data)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.active_connections.discard(ws)

    async def send_personal(self, websocket: WebSocket, message: dict):
        try:
            await websocket.send_text(json.dumps(message, default=str))
        except Exception as e:
            log.error("ws_send_error", error=str(e))

manager = ConnectionManager()
