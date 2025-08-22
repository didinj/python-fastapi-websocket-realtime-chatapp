from typing import Dict, Set
from fastapi import WebSocket


class ConnectionManager:
    """Keeps a set of active WebSocket connections and broadcasts messages."""


    def __init__(self) -> None:
        self.active_connections: Set[WebSocket] = set()


    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)


    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.discard(websocket)


    async def broadcast(self, message: str) -> None:
        to_remove = []
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception:
                # connection likely closed
                to_remove.append(connection)
        for conn in to_remove:
            self.disconnect(conn)

class RoomedConnectionManager:
    def __init__(self) -> None:
        self.rooms: Dict[str, Set[WebSocket]] = {}


    async def connect(self, room: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.rooms.setdefault(room, set()).add(websocket)


    def disconnect(self, room: str, websocket: WebSocket) -> None:
        if room in self.rooms:
            self.rooms[room].discard(websocket)
            if not self.rooms[room]:
                self.rooms.pop(room, None)


    async def broadcast(self, room: str, message: str) -> None:
        for ws in list(self.rooms.get(room, [])):
            try:
                await ws.send_text(message)
            except Exception:
                self.disconnect(room, ws)