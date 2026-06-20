"""NOC Agentic AI — FastAPI Application Entry Point"""
import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import alarms, tickets, migration, mdt, reports, websocket
from app.services.nms_simulator import nms_simulator
from app.services.alarm_processor import process_alarm
from app.api.routes.alarms import add_alarm, store_result
from app.api.routes.tickets import add_ticket
from app.api.routes.migration import add_migration
from app.api.routes.mdt import add_mdt


async def on_alarm_received(alarm_data: dict):
    """Callback: new alarm from NMS simulator → run through agent pipeline."""
    add_alarm(alarm_data)
    result = await process_alarm(alarm_data)

    if result.get("ticket_result"):
        ticket = result["ticket_result"]
        ticket["alarm_id"] = alarm_data["id"]
        add_ticket(ticket)

    if result.get("migration_plan"):
        plan = result["migration_plan"]
        plan["alarm_id"] = alarm_data["id"]
        plan["status"] = "PENDING_APPROVAL"
        add_migration(plan)

    if result.get("mdt_plan"):
        plan = result["mdt_plan"]
        plan["alarm_id"] = alarm_data["id"]
        plan["status"] = "PENDING"
        add_mdt(plan)

    store_result(alarm_data["id"], {
        "triage": result.get("triage_result"),
        "rca": result.get("rca_result"),
        "ticket": result.get("ticket_result"),
        "notification": result.get("notification_result"),
    })


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if settings.NMS_SIMULATE:
        nms_simulator.add_callback(on_alarm_received)
        asyncio.create_task(nms_simulator.start())
        print("NMS Simulator started")
    yield
    # Shutdown
    nms_simulator.stop()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="NOC Agentic AI — Real-time optical network alarm management with LangGraph agents",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(alarms.router, prefix="/api/v1")
app.include_router(tickets.router, prefix="/api/v1")
app.include_router(migration.router, prefix="/api/v1")
app.include_router(mdt.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(websocket.router)


@app.get("/")
async def root():
    return {"app": settings.APP_NAME, "version": settings.APP_VERSION, "status": "operational"}


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "noc-backend"}
