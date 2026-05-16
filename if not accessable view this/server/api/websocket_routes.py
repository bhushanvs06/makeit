from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.websocket_manager import manager

router = APIRouter()

@router.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # keep connection alive, receive pings if needed
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)