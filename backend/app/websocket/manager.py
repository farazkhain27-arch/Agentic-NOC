"""WebSocket connection manager for real-time alarm broadcasting."""
import json
from typing import Dict, List, Set
from fastapi import WebSocket
import asyncio


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

    async def broadcast(self, event_type: str, data: dict):
        message = json.dumps({"type": event_type, "data": data, "timestamp": __import__('datetime').datetime.utcnow().isoformat()})
        dead = []
        async with self._lock:
            connections = list(self.active_connections)
        for ws in connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(ws)

    async def send_personal(self, websocket: WebSocket, event_type: str, data: dict):
        message = json.dumps({"type": event_type, "data": data})
        await websocket.send_text(message)


ws_manager = ConnectionManager()
