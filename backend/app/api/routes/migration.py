from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/migration", tags=["migration"])
_migrations: List[Dict] = []


class ApprovalRequest(BaseModel):
    approved: bool
    approved_by: str
    notes: Optional[str] = None


@router.get("/")
async def get_migrations():
    return list(reversed(_migrations))


@router.get("/pending")
async def get_pending_migrations():
    return [m for m in _migrations if m.get("status") == "PENDING_APPROVAL"]


@router.post("/{migration_id}/approve")
async def approve_migration(migration_id: str, approval: ApprovalRequest):
    m = next((m for m in _migrations if m.get("id") == migration_id), None)
    if not m:
        raise HTTPException(status_code=404, detail="Migration request not found")
    m["status"] = "APPROVED" if approval.approved else "REJECTED"
    m["approved_by"] = approval.approved_by
    m["approved_at"] = datetime.utcnow().isoformat()
    m["notes"] = approval.notes
    return m


def add_migration(migration: Dict):
    import uuid
    migration["id"] = str(uuid.uuid4())
    _migrations.append(migration)
