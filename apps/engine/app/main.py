import argparse
import asyncio
import hmac
import logging
import re
from datetime import datetime, timezone
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, status
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.events import event_bus, EventEnvelope
from app.infrastructure.database.session import init_db, recover_interrupted_operations
from app.infrastructure.fts.fts_manager import FTSManager

# API Routers
from app.api.v1.scans import router as scans_router
from app.api.v1.posts import router as posts_router
from app.api.v1.persons import router as persons_router
from app.api.v1.customers import router as customers_router
from app.api.v1.care import router as care_router
from app.api.v1.search import router as search_router
from app.api.v1.backup import router as backup_router
from app.api.v1.workspace import router as workspace_router
from app.api.v1.integrations import router as integrations_router
from app.api.v1.campaigns import router as campaigns_router
from app.api.v1.scans import workers
from app.infrastructure.database.session import SessionLocal
from app.infrastructure.database.models import (
    CareTaskDB,
)
from app.modules.scanner.retention import retention_cleaner
from app.core.runtime import operation_lock


async def maintenance():
    reminded = set()
    while True:
        async with operation_lock:
            await maintain_once(reminded)
        await asyncio.sleep(60)


async def maintain_once(reminded):
    with SessionLocal() as db:
        if settings.RAW_SCAN_RETENTION_HOURS > 0:
            retention_cleaner.cleanup_expired_raw_scans(
                db, settings.RAW_SCAN_RETENTION_HOURS
            )
        due = (
            db.query(CareTaskDB)
            .filter(
                CareTaskDB.status == "PENDING",
                CareTaskDB.deleted_at.is_(None),
                CareTaskDB.scheduled_at <= datetime.now(timezone.utc),
            )
            .all()
        )
        for task in due:
            if task.id not in reminded:
                await event_bus.publish(
                    "CARE_TASK_DUE", "care", {"task_id": task.id, "title": task.title}
                )
                reminded.add(task.id)
        reminded.intersection_update(t.id for t in due)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize tables and FTS5 index
    init_db()
    FTSManager.install_sync()
    recover_interrupted_operations()
    print(f"[*] ScanSocial Engine started on {settings.HOST}:{settings.PORT}")
    maintenance_task = asyncio.create_task(maintenance())
    try:
        yield
    finally:
        tasks = [maintenance_task, *workers.values()]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        workers.clear()
    print("[*] ScanSocial Engine shutting down gracefully")


app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan)


@app.middleware("http")
async def serialize_database_requests(request, call_next):
    if request.url.path.startswith("/api/v1"):
        async with operation_lock:
            return await call_next(request)
    return await call_next(request)


# CORS configuration for local Tauri frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
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
app.include_router(workspace_router, prefix=api_v1_prefix)
app.include_router(integrations_router, prefix=api_v1_prefix)
app.include_router(campaigns_router, prefix=api_v1_prefix)

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
    if not hmac.compare_digest(token.encode(), settings.SESSION_TOKEN.encode()):
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
    with SessionLocal() as db:
        from sqlalchemy import text

        db.execute(text("SELECT 1"))
    return {
        "status": "HEALTHY",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": "CONNECTED",
    }


def run():
    parser = argparse.ArgumentParser(description="ScanSocial Local Backend Engine")
    parser.add_argument(
        "--port", type=int, default=settings.PORT, help="Port to bind (127.0.0.1)"
    )
    parser.add_argument(
        "--session-token", type=str, default=None, help="Ephemeral session secret token"
    )
    args = parser.parse_args()

    if args.port:
        settings.PORT = args.port
    if args.session_token:
        settings.SESSION_TOKEN = args.session_token

    config = uvicorn.Config(
        app, host=settings.HOST, port=settings.PORT, log_level="info"
    )

    class RedactSessionToken(logging.Filter):
        def filter(self, record):
            def redact(value):
                return (
                    re.sub(r"(token=)[^\s\"\]]+", r"\1[REDACTED]", value)
                    if isinstance(value, str)
                    else value
                )

            record.msg = redact(record.msg)
            if isinstance(record.args, tuple):
                record.args = tuple(redact(arg) for arg in record.args)
            return True

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(logger_name).addFilter(RedactSessionToken())
    uvicorn.Server(config).run()


if __name__ == "__main__":
    run()
