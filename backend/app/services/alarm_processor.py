"""Alarm processor — receives raw NMS alarms, runs through LangGraph pipeline, persists to DB, broadcasts via WS."""
import json
import asyncio
from typing import Dict, Any
from datetime import datetime, timezone
from app.agents.graph import noc_graph
from app.agents.state import NOCState
from app.websocket.manager import ws_manager


async def process_alarm(alarm_data: Dict[str, Any], db_session=None) -> Dict[str, Any]:
    """Run a raw alarm through the full NOC agent pipeline."""
    initial_state: NOCState = {
        "alarm": alarm_data,
        "messages": [],
        "triage_result": None,
        "rca_result": None,
        "migration_plan": None,
        "mdt_plan": None,
        "ticket_result": None,
        "notification_result": None,
        "report_data": None,
        "requires_migration": False,
        "requires_mdt": False,
        "requires_human_approval": False,
        "human_approved": None,
        "approval_type": None,
        "severity_level": None,
        "error": None,
        "processing_complete": False,
    }

    config = {"configurable": {"thread_id": alarm_data.get("id", "default")}}

    try:
        final_state = await asyncio.get_event_loop().run_in_executor(
            None, lambda: noc_graph.invoke(initial_state, config)
        )

        # Broadcast alarm + results to all connected WebSocket clients
        await ws_manager.broadcast("alarm_processed", {
            "alarm": alarm_data,
            "severity": final_state.get("severity_level"),
            "ticket": final_state.get("ticket_result"),
            "rca": final_state.get("rca_result"),
            "requires_approval": final_state.get("requires_human_approval"),
            "approval_type": final_state.get("approval_type"),
            "migration_plan": final_state.get("migration_plan"),
            "mdt_plan": final_state.get("mdt_plan"),
        })

        return final_state

    except Exception as e:
        error_data = {"error": str(e), "alarm_id": alarm_data.get("id")}
        await ws_manager.broadcast("alarm_error", error_data)
        return {**initial_state, "error": str(e)}
