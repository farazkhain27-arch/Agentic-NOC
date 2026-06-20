from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, update
from typing import Optional, List
from datetime import datetime, date, timezone
import uuid
import json

from app.db.database import get_db
from app.models.models import (
    Alarm, Ticket, Migration, MDT, AgentEvent, DailyReport,
    NetworkElement, AlarmStatus, MigrationStatus, MDTStatus, TicketStatus
)
from app.core.websocket_manager import manager

router = APIRouter()

# ─── Alarms ─────────────────────────────────────────────────────────────────────
@router.get("/alarms")
async def list_alarms(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    q = select(Alarm).order_by(desc(Alarm.detected_at)).limit(limit).offset(offset)
    if status:
        q = q.where(Alarm.status == status)
    if severity:
        q = q.where(Alarm.severity == severity)
    result = await db.execute(q)
    alarms = result.scalars().all()
    return [_alarm_dict(a) for a in alarms]

@router.get("/alarms/stats")
async def alarm_stats(db: AsyncSession = Depends(get_db)):
    total = await db.scalar(select(func.count()).select_from(Alarm))
    active = await db.scalar(select(func.count()).select_from(Alarm).where(Alarm.status == "ACTIVE"))
    critical = await db.scalar(select(func.count()).select_from(Alarm).where(Alarm.severity == "CRITICAL", Alarm.status == "ACTIVE"))
    high = await db.scalar(select(func.count()).select_from(Alarm).where(Alarm.severity == "HIGH", Alarm.status == "ACTIVE"))
    memo = await db.scalar(select(func.count()).select_from(Alarm).where(Alarm.severity == "MEMO", Alarm.status == "ACTIVE"))
    resolved_today = await db.scalar(
        select(func.count()).select_from(Alarm)
        .where(Alarm.status == "RESOLVED", func.date(Alarm.resolved_at) == date.today())
    )
    return {
        "total": total, "active": active, "critical": critical,
        "high": high, "memo": memo, "resolved_today": resolved_today,
    }

@router.patch("/alarms/{alarm_id}/acknowledge")
async def acknowledge_alarm(alarm_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Alarm).where(Alarm.alarm_id == alarm_id))
    alarm = result.scalar_one_or_none()
    if not alarm:
        raise HTTPException(404, "Alarm not found")
    alarm.status = AlarmStatus.ACKNOWLEDGED
    alarm.acknowledged_at = datetime.now(timezone.utc)
    await db.commit()
    await manager.broadcast({"type": "alarm_updated", "alarm_id": alarm_id, "status": "ACKNOWLEDGED"})
    return {"status": "acknowledged"}

@router.patch("/alarms/{alarm_id}/resolve")
async def resolve_alarm(alarm_id: str, resolution: dict = {}, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Alarm).where(Alarm.alarm_id == alarm_id))
    alarm = result.scalar_one_or_none()
    if not alarm:
        raise HTTPException(404, "Alarm not found")
    alarm.status = AlarmStatus.RESOLVED
    alarm.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await manager.broadcast({"type": "alarm_updated", "alarm_id": alarm_id, "status": "RESOLVED"})
    return {"status": "resolved"}

# ─── Tickets ─────────────────────────────────────────────────────────────────────
@router.get("/tickets")
async def list_tickets(
    status: Optional[str] = None,
    ticket_type: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    q = select(Ticket).order_by(desc(Ticket.created_at)).limit(limit)
    if status:
        q = q.where(Ticket.status == status)
    if ticket_type:
        q = q.where(Ticket.ticket_type == ticket_type)
    result = await db.execute(q)
    tickets = result.scalars().all()
    return [_ticket_dict(t) for t in tickets]

@router.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Ticket).where(Ticket.ticket_number == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    return _ticket_dict(ticket)

@router.patch("/tickets/{ticket_id}/status")
async def update_ticket_status(ticket_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Ticket).where(Ticket.ticket_number == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    ticket.status = body.get("status", ticket.status)
    if body.get("resolution"):
        ticket.resolution = body["resolution"]
    if body.get("rfo"):
        ticket.rfo = body["rfo"]
    ticket.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await manager.broadcast({"type": "ticket_updated", "ticket_number": ticket_id})
    return {"status": "updated"}

# ─── Migrations ──────────────────────────────────────────────────────────────────
@router.get("/migrations")
async def list_migrations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Migration).order_by(desc(Migration.created_at)).limit(50))
    migrations = result.scalars().all()
    return [_migration_dict(m) for m in migrations]

@router.post("/migrations/{migration_id}/approve")
async def approve_migration(migration_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Migration).where(Migration.id == uuid.UUID(migration_id)))
    migration = result.scalar_one_or_none()
    if not migration:
        raise HTTPException(404, "Migration not found")
    migration.status = MigrationStatus.APPROVED
    migration.approved_by = body.get("approved_by", "NOC-Engineer")
    migration.approval_notes = body.get("notes", "")
    migration.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await manager.broadcast({"type": "migration_approved", "migration_id": migration_id})
    return {"status": "approved"}

@router.post("/migrations/{migration_id}/reject")
async def reject_migration(migration_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Migration).where(Migration.id == uuid.UUID(migration_id)))
    migration = result.scalar_one_or_none()
    if not migration:
        raise HTTPException(404, "Migration not found")
    migration.status = MigrationStatus.REJECTED
    migration.approved_by = body.get("rejected_by", "NOC-Engineer")
    migration.approval_notes = body.get("notes", "")
    migration.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await manager.broadcast({"type": "migration_rejected", "migration_id": migration_id})
    return {"status": "rejected"}

# ─── MDT ─────────────────────────────────────────────────────────────────────────
@router.get("/mdts")
async def list_mdts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MDT).order_by(desc(MDT.created_at)).limit(50))
    mdts = result.scalars().all()
    return [_mdt_dict(m) for m in mdts]

@router.post("/mdts/{mdt_id}/approve")
async def approve_mdt(mdt_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MDT).where(MDT.id == uuid.UUID(mdt_id)))
    mdt = result.scalar_one_or_none()
    if not mdt:
        raise HTTPException(404, "MDT not found")
    mdt.status = MDTStatus.APPROVED
    mdt.approved_by = body.get("approved_by", "NOC-Manager")
    mdt.approval_notes = body.get("notes", "")
    mdt.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await manager.broadcast({"type": "mdt_approved", "mdt_id": mdt_id})
    return {"status": "approved"}

@router.post("/mdts/{mdt_id}/reject")
async def reject_mdt(mdt_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MDT).where(MDT.id == uuid.UUID(mdt_id)))
    mdt = result.scalar_one_or_none()
    if not mdt:
        raise HTTPException(404, "MDT not found")
    mdt.status = MDTStatus.REJECTED
    mdt.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "rejected"}

@router.post("/mdts/{mdt_id}/complete")
async def complete_mdt(mdt_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MDT).where(MDT.id == uuid.UUID(mdt_id)))
    mdt = result.scalar_one_or_none()
    if not mdt:
        raise HTTPException(404, "MDT not found")
    mdt.status = MDTStatus.COMPLETED
    mdt.actual_end = datetime.now(timezone.utc)
    mdt.post_mdt_verification = body.get("verification", "")
    mdt.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "completed"}

# ─── Reports ─────────────────────────────────────────────────────────────────────
@router.get("/reports")
async def list_reports(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DailyReport).order_by(desc(DailyReport.report_date)).limit(30))
    reports = result.scalars().all()
    return [_report_dict(r) for r in reports]

@router.post("/reports/generate")
async def generate_report(db: AsyncSession = Depends(get_db)):
    today = date.today().isoformat()
    total = await db.scalar(select(func.count()).select_from(Alarm).where(func.date(Alarm.detected_at) == date.today()))
    critical = await db.scalar(select(func.count()).select_from(Alarm).where(Alarm.severity == "CRITICAL", func.date(Alarm.detected_at) == date.today()))
    high = await db.scalar(select(func.count()).select_from(Alarm).where(Alarm.severity == "HIGH", func.date(Alarm.detected_at) == date.today()))
    memo_count = await db.scalar(select(func.count()).select_from(Alarm).where(Alarm.severity == "MEMO", func.date(Alarm.detected_at) == date.today()))
    tickets_opened = await db.scalar(select(func.count()).select_from(Ticket).where(func.date(Ticket.created_at) == date.today()))
    tickets_resolved = await db.scalar(select(func.count()).select_from(Ticket).where(Ticket.status == "RESOLVED", func.date(Ticket.resolved_at) == date.today()))

    report_content = f"""NOC DAILY REPORT — {today}
{'='*50}
Total Alarms    : {total}
  Critical      : {critical}
  High          : {high}
  Memo          : {memo_count}
Tickets Opened  : {tickets_opened}
Tickets Resolved: {tickets_resolved}
Generated       : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
Generated by    : NOC Agentic AI System
"""
    report = DailyReport(
        report_date=today,
        total_alarms=total or 0,
        critical_alarms=critical or 0,
        high_alarms=high or 0,
        memo_alarms=memo_count or 0,
        tickets_opened=tickets_opened or 0,
        tickets_resolved=tickets_resolved or 0,
        report_content=report_content,
    )
    db.add(report)
    await db.commit()
    return _report_dict(report)

# ─── Agent Events ─────────────────────────────────────────────────────────────────
@router.get("/agent-events")
async def list_agent_events(limit: int = Query(100, le=500), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentEvent).order_by(desc(AgentEvent.created_at)).limit(limit))
    events = result.scalars().all()
    return [_event_dict(e) for e in events]

# ─── Network Elements ─────────────────────────────────────────────────────────────
@router.get("/network-elements")
async def list_network_elements(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NetworkElement))
    nes = result.scalars().all()
    return [{"id": str(ne.id), "ne_id": ne.ne_id, "name": ne.name, "ne_type": ne.ne_type,
             "site_name": ne.site_name, "region": ne.region, "status": ne.status,
             "vendor": ne.vendor} for ne in nes]

# ─── Serializers ────────────────────────────────────────────────────────────────
def _alarm_dict(a):
    return {
        "id": str(a.id), "alarm_id": a.alarm_id, "alarm_code": a.alarm_code,
        "alarm_type": a.alarm_type, "severity": a.severity.value if a.severity else None,
        "status": a.status.value if a.status else None, "description": a.description,
        "affected_circuits": a.affected_circuits, "pm_data": a.pm_data,
        "detected_at": a.detected_at.isoformat() if a.detected_at else None,
        "acknowledged_at": a.acknowledged_at.isoformat() if a.acknowledged_at else None,
        "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
        "ticket_id": a.ticket_id, "agent_rca": a.agent_rca,
        "agent_confidence": float(a.agent_confidence) if a.agent_confidence else None,
    }

def _ticket_dict(t):
    return {
        "id": str(t.id), "ticket_number": t.ticket_number, "jira_key": t.jira_key,
        "ticket_type": t.ticket_type.value if t.ticket_type else None,
        "status": t.status.value if t.status else None, "title": t.title,
        "description": t.description, "impact_statement": t.impact_statement,
        "assignee": t.assignee, "reporter": t.reporter, "rfo": t.rfo,
        "resolution": t.resolution,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        "resolved_at": t.resolved_at.isoformat() if t.resolved_at else None,
    }

def _migration_dict(m):
    return {
        "id": str(m.id), "alarm_id": str(m.alarm_id) if m.alarm_id else None,
        "affected_circuits": m.affected_circuits, "migration_plan": m.migration_plan,
        "status": m.status.value if m.status else None, "proposed_by": m.proposed_by,
        "approved_by": m.approved_by, "approval_notes": m.approval_notes,
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "updated_at": m.updated_at.isoformat() if m.updated_at else None,
        "started_at": m.started_at.isoformat() if m.started_at else None,
        "completed_at": m.completed_at.isoformat() if m.completed_at else None,
    }

def _mdt_dict(m):
    return {
        "id": str(m.id), "mdt_number": m.mdt_number,
        "alarm_id": str(m.alarm_id) if m.alarm_id else None,
        "title": m.title, "description": m.description,
        "maintenance_type": m.maintenance_type,
        "affected_services": m.affected_services,
        "status": m.status.value if m.status else None,
        "requested_by": m.requested_by, "approved_by": m.approved_by,
        "approval_notes": m.approval_notes,
        "commands_executed": m.commands_executed,
        "post_mdt_verification": m.post_mdt_verification,
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "updated_at": m.updated_at.isoformat() if m.updated_at else None,
    }

def _report_dict(r):
    return {
        "id": str(r.id), "report_date": r.report_date,
        "total_alarms": r.total_alarms, "critical_alarms": r.critical_alarms,
        "high_alarms": r.high_alarms, "memo_alarms": r.memo_alarms,
        "tickets_opened": r.tickets_opened, "tickets_resolved": r.tickets_resolved,
        "migrations_performed": r.migrations_performed, "mdts_performed": r.mdts_performed,
        "avg_mttr_minutes": float(r.avg_mttr_minutes) if r.avg_mttr_minutes else None,
        "report_content": r.report_content,
        "sent_at": r.sent_at.isoformat() if r.sent_at else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }

def _event_dict(e):
    return {
        "id": str(e.id), "alarm_id": str(e.alarm_id) if e.alarm_id else None,
        "agent_name": e.agent_name, "action": e.action,
        "output_data": e.output_data, "duration_ms": e.duration_ms,
        "success": e.success, "error_message": e.error_message,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }
