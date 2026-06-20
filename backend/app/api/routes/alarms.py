from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

router = APIRouter(prefix="/alarms", tags=["alarms"])

# In-memory store (replace with DB in production)
_alarms: List[Dict] = []
_processed_results: Dict[str, Any] = {}


class AlarmResponse(BaseModel):
    id: str
    alarm_type: str
    severity: str
    status: str
    node_name: str
    node_ip: Optional[str]
    shelf: Optional[int]
    slot: Optional[int]
    port: Optional[int]
    alarm_message: Optional[str]
    detected_at: str
    jira_ticket_id: Optional[str]
    rca_summary: Optional[str]
    equipment_type: Optional[str]


@router.get("/", response_model=List[Dict])
async def get_alarms(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100
):
    """Get all active alarms with optional filtering."""
    results = _alarms[-limit:]
    if severity:
        results = [a for a in results if a.get("severity") == severity.upper()]
    if status:
        results = [a for a in results if a.get("status") == status.upper()]
    return list(reversed(results))


@router.get("/stats")
async def get_alarm_stats():
    """Get alarm statistics for dashboard."""
    total = len(_alarms)
    critical = sum(1 for a in _alarms if a.get("severity") == "CRITICAL" and a.get("status") == "ACTIVE")
    high = sum(1 for a in _alarms if a.get("severity") == "HIGH" and a.get("status") == "ACTIVE")
    memo = sum(1 for a in _alarms if a.get("severity") == "MEMO" and a.get("status") == "ACTIVE")
    resolved = sum(1 for a in _alarms if a.get("status") == "RESOLVED")
    return {
        "total": total,
        "active": total - resolved,
        "critical": critical,
        "high": high,
        "memo": memo,
        "resolved": resolved,
        "by_equipment": {
            "OTN": sum(1 for a in _alarms if a.get("equipment_type") == "OTN"),
            "SDH": sum(1 for a in _alarms if a.get("equipment_type") == "SDH"),
            "DWDM": sum(1 for a in _alarms if a.get("equipment_type") == "DWDM"),
        }
    }


@router.get("/{alarm_id}")
async def get_alarm(alarm_id: str):
    alarm = next((a for a in _alarms if a.get("id") == alarm_id), None)
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm not found")
    result = _processed_results.get(alarm_id, {})
    return {**alarm, "agent_results": result}


@router.post("/{alarm_id}/acknowledge")
async def acknowledge_alarm(alarm_id: str, acknowledged_by: str = "NOC Operator"):
    alarm = next((a for a in _alarms if a.get("id") == alarm_id), None)
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm not found")
    alarm["status"] = "ACKNOWLEDGED"
    alarm["acknowledged_by"] = acknowledged_by
    alarm["acknowledged_at"] = datetime.utcnow().isoformat()
    return {"message": "Alarm acknowledged", "alarm_id": alarm_id}


@router.post("/{alarm_id}/resolve")
async def resolve_alarm(alarm_id: str, resolved_by: str = "NOC Operator"):
    alarm = next((a for a in _alarms if a.get("id") == alarm_id), None)
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm not found")
    alarm["status"] = "RESOLVED"
    alarm["resolved_at"] = datetime.utcnow().isoformat()
    return {"message": "Alarm resolved", "alarm_id": alarm_id}


def add_alarm(alarm: Dict):
    _alarms.append(alarm)
    if len(_alarms) > 500:
        _alarms.pop(0)

def store_result(alarm_id: str, result: Dict):
    _processed_results[alarm_id] = result
