from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import json

from .manager import ConnectionManager
from .utils import verify_token
from fastapi import Depends
from .redis_broadcast import RedisBroadcaster

app = FastAPI(title="FastAPI Real-Time Chat")
manager = ConnectionManager()
broadcaster = RedisBroadcaster()

# (Optional) CORS if you serve a separate frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (our simple chat UI)
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def root():
    # Return the HTML client
    html_path = static_dir / "index.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    username = websocket.query_params.get("username", "Guest")
    room = websocket.query_params.get("room", "lobby")


    await manager.connect(room, websocket)
    await manager.broadcast(room, json.dumps({"type": "system", "message": f"{username} joined {room}"}))
    try:
        while True:
            text = await websocket.receive_text()
            await manager.broadcast(room, json.dumps({"type": "chat", "user": username, "message": text}))
    except WebSocketDisconnect:
        manager.disconnect(room, websocket)
        await manager.broadcast(room, json.dumps({"type": "system", "message": f"{username} left {room}"}))

@app.websocket("/ws-secure")
async def ws_secure(websocket: WebSocket):
    token = websocket.query_params.get("token")
    username = verify_token(token) if token else None
    if not username:
        await websocket.close(code=4401) # 4401 Unauthorized
        return

    await manager.connect(websocket)
    await manager.broadcast(json.dumps({"type": "system", "message": f"{username} joined"}))
    try:
        while True:
            text = await websocket.receive_text()
            await manager.broadcast(json.dumps({"type": "chat", "user": username, "message": text}))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(json.dumps({"type": "system", "message": f"{username} left"}))

@app.get("/token")
async def token(username: str):
    from .utils import issue_token
    return {"token": issue_token(username)}

@app.on_event("startup")
async def on_start():
    await broadcaster.start()

@app.on_event("shutdown")
async def on_stop():
    await broadcaster.stop()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    username = websocket.query_params.get("username", "Guest")
    await broadcaster.connect(websocket)
    await broadcaster.broadcast(json.dumps({"type": "system", "message": f"{username} joined"}))
    try:
        while True:
            text = await websocket.receive_text()
            await broadcaster.broadcast(json.dumps({"type": "chat", "user": username, "message": text}))
    except WebSocketDisconnect:
        broadcaster.disconnect(websocket)
        await broadcaster.broadcast(json.dumps({"type": "system", "message": f"{username} left"}))