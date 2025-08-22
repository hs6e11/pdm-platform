from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging
from .connection_manager import manager

router = APIRouter()

@router.websocket("/ws/client/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, client_id)
