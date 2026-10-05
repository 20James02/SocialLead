import argparse
import asyncio
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, status
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.events import event_bus, EventEnvelope
from app.infrastructure.database.session import init_db
from app.infrastructure.fts.fts_manager import FTSManager

# API Routers
from app.api.v1.scans import router as scans_router
from app.api.v1.posts import router as posts_router
from app.api.v1.persons import router as persons_router
from app.api.v1.customers import router as customers_router
from app.api.v1.care import router as care_router
from app.api.v1.search import router as search_router
from app.api.v1.backup import router as backup_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize tables and FTS5 index
    init_db()
    FTSManager.init_fts_table()
    print(f"[*] ScanSocial Engine started on {settings.HOST}:{settings.PORT}")
    print(f"[*] Session Auth Token: {settings.SESSION_TOKEN}")
    yield
    print("[*] ScanSocial Engine shutting down gracefully")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# CORS configuration for local Tauri frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API v1 Routers
api_v1_prefix = "/api/v1"
app.include_router(scans_router, prefix=api_v1_prefix)
app.include_router(posts_router, prefix=api_v1_prefix)
app.include_router(persons_router, prefix=api_v1_prefix)
app.include_router(customers_router, prefix=api_v1_prefix)
app.include_router(care_router, prefix=api_v1_prefix)
app.include_router(search_router, prefix=api_v1_prefix)
app.include_router(backup_router, prefix=api_v1_prefix)

# Active WebSocket clients
connected_clients: list[WebSocket] = []

async def on_bus_event(event: EventEnvelope):
    """Broadcasts all application events to connected WebSocket desktop UI clients."""
    if not connected_clients:
        return
    payload = event.model_dump_json()
    for ws in list(connected_clients):
        try:
            await ws.send_text(payload)
        except Exception:
            if ws in connected_clients:
                connected_clients.remove(ws)

# Subscribe to all internal events
event_bus.subscribe("*", on_bus_event)

@app.websocket("/ws/live")
async def websocket_live_endpoint(websocket: WebSocket, token: str = Query(...)):
    if token != settings.SESSION_TOKEN:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in connected_clients:
            connected_clients.remove(websocket)

@app.get("/health")
def health_check():
    return {
        "status": "HEALTHY",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": "CONNECTED"
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ScanSocial Local Backend Engine")
    parser.add_argument("--port", type=int, default=settings.PORT, help="Port to bind (127.0.0.1)")
    parser.add_argument("--session-token", type=str, default=None, help="Ephemeral session secret token")
    args = parser.parse_args()

    if args.port:
        settings.PORT = args.port
    if args.session_token:
        settings.SESSION_TOKEN = args.session_token

    uvicorn.run(app, host=settings.HOST, port=settings.PORT, log_level="info")
