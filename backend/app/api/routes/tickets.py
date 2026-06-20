from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/tickets", tags=["tickets"])
_tickets: List[Dict] = []


@router.get("/")
async def get_tickets(status: Optional[str] = None, priority: Optional[str] = None, limit: int = 50):
    results = _tickets[-limit:]
    if status:
        results = [t for t in results if t.get("status", "").lower() == status.lower()]
    if priority:
        results = [t for t in results if t.get("priority", "").lower() == priority.lower()]
    return list(reversed(results))


@router.get("/stats")
async def ticket_stats():
    return {
        "total": len(_tickets),
        "open": sum(1 for t in _tickets if t.get("status") == "Open"),
        "in_progress": sum(1 for t in _tickets if t.get("status") == "In Progress"),
        "resolved": sum(1 for t in _tickets if t.get("status") == "Resolved"),
    }


@router.get("/{ticket_id}")
async def get_ticket(ticket_id: str):
    t = next((t for t in _tickets if t.get("jira_key") == ticket_id or t.get("id") == ticket_id), None)
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return t


@router.patch("/{ticket_id}/status")
async def update_ticket_status(ticket_id: str, status: str):
    t = next((t for t in _tickets if t.get("jira_key") == ticket_id), None)
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    t["status"] = status
    t["updated_at"] = datetime.utcnow().isoformat()
    return t


def add_ticket(ticket: Dict):
    _tickets.append(ticket)
