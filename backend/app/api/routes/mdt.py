from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid

router = APIRouter(prefix="/mdt", tags=["mdt"])
_mdts: List[Dict] = []


class MDTCreate(BaseModel):
    node_name: str
    shelf: str
    slot: str
    reason: str
    scheduled_start: str
    scheduled_end: str
    requested_by: str
    affected_circuits: Optional[List[str]] = []


class ApprovalRequest(BaseModel):
    approved: bool
    approved_by: str
    notes: Optional[str] = None


@router.get("/")
async def get_mdts(status: Optional[str] = None):
    if status:
        return [m for m in _mdts if m.get("status") == status]
    return list(reversed(_mdts))


@router.post("/")
async def create_mdt(mdt: MDTCreate):
    record = {
        "id": str(uuid.uuid4()),
        "status": "PENDING",
        "created_at": datetime.utcnow().isoformat(),
        **mdt.model_dump()
    }
    _mdts.append(record)
    return record


@router.post("/{mdt_id}/approve")
async def approve_mdt(mdt_id: str, approval: ApprovalRequest):
    m = next((m for m in _mdts if m.get("id") == mdt_id), None)
    if not m:
        raise HTTPException(status_code=404, detail="MDT not found")
    m["status"] = "APPROVED" if approval.approved else "REJECTED"
    m["approved_by"] = approval.approved_by
    m["approved_at"] = datetime.utcnow().isoformat()
    return m


@router.post("/{mdt_id}/complete")
async def complete_mdt(mdt_id: str):
    m = next((m for m in _mdts if m.get("id") == mdt_id), None)
    if not m:
        raise HTTPException(status_code=404, detail="MDT not found")
    m["status"] = "COMPLETED"
    m["actual_end"] = datetime.utcnow().isoformat()
    return m


def add_mdt(mdt: Dict):
    mdt["id"] = str(uuid.uuid4())
    _mdts.append(mdt)
