import asyncio
import json
import os
from typing import Set
from fastapi import WebSocket
import redis.asyncio as redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

class RedisBroadcaster:
    def __init__(self) -> None:
        self.local_clients: Set[WebSocket] = set()
        self.r = redis.from_url(REDIS_URL, decode_responses=True)
        self.channel = "chat:global"
        self._sub_task: asyncio.Task | None = None

    async def start(self) -> None:
        async def reader():
            pubsub = self.r.pubsub()
            await pubsub.subscribe(self.channel)
            async for msg in pubsub.listen():
                if msg.get("type") == "message":
                    data = msg.get("data")
                    # fan-out to local websockets
                    dead = []
                    for ws in list(self.local_clients):
                        try:
                            await ws.send_text(data)
                        except Exception:
                            dead.append(ws)
                    for d in dead:
                        self.local_clients.discard(d)
        self._sub_task = asyncio.create_task(reader())

    async def stop(self) -> None:
        if self._sub_task:
            self._sub_task.cancel()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.local_clients.add(ws)

    def disconnect(self, ws: WebSocket):
        self.local_clients.discard(ws)

    async def broadcast(self, message: str):
        await self.r.publish(self.channel, message)