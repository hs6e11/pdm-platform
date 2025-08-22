from typing import Dict, List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = []
        self.active_connections[client_id].append(websocket)
        
    def disconnect(self, websocket: WebSocket, client_id: str):
        if client_id in self.active_connections:
            if websocket in self.active_connections[client_id]:
                self.active_connections[client_id].remove(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]

    async def broadcast_to_client(self, message: str, client_id: str):
        if client_id in self.active_connections:
            dead_connections = []
            for connection in self.active_connections[client_id]:
                try:
                    await connection.send_text(message)
                except:
                    dead_connections.append(connection)
            
            # Remove dead connections
            for dead_conn in dead_connections:
                self.active_connections[client_id].remove(dead_conn)

# Global instance
manager = ConnectionManager()
