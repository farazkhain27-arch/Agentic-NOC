from fastapi import APIRouter
from datetime import datetime, timedelta, timezone
from typing import List, Dict
import random

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/daily")
async def get_daily_report():
    """Generate daily shift report."""
    now = datetime.now(timezone.utc)
    return {
        "report_date": now.date().isoformat(),
        "generated_at": now.isoformat(),
        "shift_summary": {
            "total_alarms": random.randint(8, 24),
            "critical": random.randint(1, 4),
            "high": random.randint(2, 8),
            "memo": random.randint(3, 12),
            "resolved": random.randint(5, 18),
            "pending": random.randint(0, 4),
        },
        "mttr_minutes": round(random.uniform(18, 45), 1),
        "mttd_seconds": round(random.uniform(30, 90), 1),
        "tickets_created": random.randint(4, 12),
        "migrations_executed": random.randint(0, 3),
        "mdts_completed": random.randint(0, 2),
        "top_affected_nodes": [
            {"node": "RIYADH-OTN-01", "alarm_count": random.randint(2, 6)},
            {"node": "JEDDAH-SDH-02", "alarm_count": random.randint(1, 4)},
            {"node": "DAMMAM-DWDM-03", "alarm_count": random.randint(0, 3)},
        ],
        "alarm_type_breakdown": {
            "LOS": random.randint(1, 4), "LOF": random.randint(0, 3),
            "AIS": random.randint(1, 5), "BER_EXC": random.randint(0, 4),
            "EQ_FAIL": random.randint(0, 2), "FAN_FAIL": random.randint(0, 3),
        }
    }


@router.get("/trend")
async def get_alarm_trend():
    """7-day alarm trend data."""
    data = []
    for i in range(7, 0, -1):
        day = datetime.now(timezone.utc) - timedelta(days=i)
        data.append({
            "date": day.date().isoformat(),
            "critical": random.randint(0, 5),
            "high": random.randint(2, 10),
            "memo": random.randint(3, 15),
            "total": random.randint(5, 30),
        })
    return data
