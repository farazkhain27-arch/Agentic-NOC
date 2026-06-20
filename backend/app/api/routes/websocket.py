from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.websocket.manager import ws_manager

router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        await ws_manager.send_personal(websocket, "connected", {"message": "NOC WebSocket connected. Awaiting alarm stream."})
        while True:
            data = await websocket.receive_text()
            # Echo heartbeat
            await ws_manager.send_personal(websocket, "pong", {"received": data})
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
