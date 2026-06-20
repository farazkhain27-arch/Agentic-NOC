"""
Background alarm consumer.
Reads alarms from the Redis queue, runs the LangGraph agent pipeline,
persists results to PostgreSQL, and broadcasts updates via WebSocket.
"""
import asyncio
import json
import uuid
from datetime import datetime, timezone
import structlog

from app.db.database import AsyncSessionLocal, get_redis_client
from app.models.models import Alarm, Ticket, Migration, MDT, AgentEvent, AlarmSeverity, AlarmStatus, TicketType, TicketStatus, MigrationStatus, MDTStatus
from app.agents.noc_pipeline import process_alarm
from app.core.websocket_manager import manager

log = structlog.get_logger()
_consumer_running = False

async def _persist_result(result: dict):
    """Save agent pipeline results to the database."""
    async with AsyncSessionLocal() as db:
        try:
            alarm_data = result.get("alarm", {})
            ticket_data = result.get("ticket_result")
            migration_data = result.get("migration_proposal")
            mdt_data = result.get("mdt_proposal")
            rca_data = result.get("rca_result", {})

            # Upsert alarm
            alarm = Alarm(
                alarm_id=alarm_data.get("alarm_id", f"ALM-{uuid.uuid4().hex[:12]}"),
                alarm_code=alarm_data.get("alarm_code", "UNKNOWN"),
                alarm_type=alarm_data.get("alarm_type"),
                severity=AlarmSeverity(alarm_data.get("severity", "MEMO")),
                status=AlarmStatus.ACTIVE,
                description=alarm_data.get("description"),
                affected_circuits=alarm_data.get("affected_circuits", []),
                pm_data=alarm_data.get("pm_data", {}),
                raw_nms_data=alarm_data,
                detected_at=datetime.now(timezone.utc),
                agent_rca=rca_data.get("root_cause") if rca_data else None,
                agent_confidence=float(rca_data.get("confidence", 0)) * 100 if rca_data else None,
            )
            db.add(alarm)
            await db.flush()

            # Create ticket
            if ticket_data:
                ticket = Ticket(
                    ticket_number=ticket_data.get("ticket_number", f"TT-{uuid.uuid4().hex[:10]}"),
                    jira_key=ticket_data.get("jira_key"),
                    alarm_id=alarm.id,
                    ticket_type=TicketType(ticket_data.get("ticket_type", "MEMO")),
                    status=TicketStatus.OPEN,
                    title=ticket_data.get("title", "NOC Alarm"),
                    description=ticket_data.get("description"),
                    impact_statement=ticket_data.get("impact_statement"),
                    assignee=ticket_data.get("assignee", "FDE-Team"),
                    reporter=ticket_data.get("reporter", "AI-Agent"),
                )
                db.add(ticket)
                await db.flush()
                alarm.ticket_id = ticket.ticket_number

            # Create migration record
            if migration_data:
                migration = Migration(
                    alarm_id=alarm.id,
                    affected_circuits=migration_data.get("circuits_to_migrate", []),
                    migration_plan=json.dumps(migration_data.get("migration_steps", [])),
                    status=MigrationStatus.PROPOSED,
                    proposed_by="AI-Agent",
                )
                db.add(migration)

            # Create MDT record
            if mdt_data:
                mdt = MDT(
                    mdt_number=mdt_data.get("mdt_number", f"MDT-{uuid.uuid4().hex[:8]}"),
                    alarm_id=alarm.id,
                    title=mdt_data.get("title", "MDT Request"),
                    description=mdt_data.get("description"),
                    maintenance_type=mdt_data.get("maintenance_type", "CARD_RESET"),
                    affected_services=mdt_data.get("affected_services", []),
                    status=MDTStatus.REQUESTED,
                    requested_by="AI-Agent",
                )
                db.add(mdt)

            # Log agent events
            for event in result.get("agent_events", []):
                ae = AgentEvent(
                    alarm_id=alarm.id,
                    agent_name=event.get("agent_name"),
                    action=event.get("action"),
                    output_data=event.get("output", {}),
                    duration_ms=event.get("duration_ms"),
                    success=True,
                )
                db.add(ae)

            await db.commit()
            return str(alarm.id)

        except Exception as e:
            await db.rollback()
            log.error("persist_error", error=str(e))
            return None

async def alarm_consumer_loop():
    """Main loop: pop from Redis queue, run pipeline, broadcast."""
    global _consumer_running
    _consumer_running = True
    log.info("alarm_consumer_started")

    redis = await get_redis_client()

    while _consumer_running:
        try:
            # Block up to 2 seconds waiting for alarm
            item = await redis.brpop("nms:alarm:queue", timeout=2)
            if not item:
                continue

            _, raw = item
            alarm = json.loads(raw)
            log.info("alarm_received", alarm_id=alarm.get("alarm_id"), severity=alarm.get("severity"))

            # Broadcast to dashboard immediately (before AI processing)
            await manager.broadcast({
                "type": "alarm_incoming",
                "alarm": alarm,
            })

            # Run agent pipeline
            result = await process_alarm(alarm)

            # Persist to DB
            alarm_db_id = await _persist_result(result)

            # Broadcast final result
            await manager.broadcast({
                "type": "alarm_processed",
                "alarm": alarm,
                "ticket": result.get("ticket_result"),
                "rca": result.get("rca_result"),
                "migration": result.get("migration_proposal"),
                "mdt": result.get("mdt_proposal"),
                "notification": result.get("notification_result"),
                "hitl_required": result.get("hitl_required", False),
                "hitl_type": result.get("hitl_type"),
                "alarm_db_id": alarm_db_id,
            })

            log.info("alarm_processed", alarm_id=alarm.get("alarm_id"))

        except asyncio.CancelledError:
            break
        except Exception as e:
            log.error("consumer_error", error=str(e))
            await asyncio.sleep(2)

    log.info("alarm_consumer_stopped")

def stop_consumer():
    global _consumer_running
    _consumer_running = False
