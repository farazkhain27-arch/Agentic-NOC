"""
LangGraph Multi-Agent NOC Pipeline
8 agents: Supervisor → Triage → RCA → Migration → MDT → Ticketing → Notification → Report
"""
import json
import time
import uuid
from datetime import datetime, timezone
from typing import TypedDict, Annotated, Optional, List, Any
import operator

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
import structlog

from app.core.config import settings

log = structlog.get_logger()

# ─── State ──────────────────────────────────────────────────────────────────────
class NOCState(TypedDict):
    alarm: dict
    ne_info: Optional[dict]
    port_info: Optional[dict]
    rca_result: Optional[dict]
    migration_proposal: Optional[dict]
    mdt_proposal: Optional[dict]
    ticket_result: Optional[dict]
    notification_result: Optional[dict]
    agent_events: Annotated[List[dict], operator.add]
    next_action: str
    hitl_required: bool
    hitl_type: Optional[str]
    error: Optional[str]

# ─── LLM ────────────────────────────────────────────────────────────────────────
def get_llm():
    return ChatAnthropic(
        model=settings.CLAUDE_MODEL,
        api_key=settings.ANTHROPIC_API_KEY,
        max_tokens=2048,
        temperature=0.1,
    )

# ─── Helper to log agent events ─────────────────────────────────────────────────
def log_event(state: NOCState, agent: str, action: str, output: dict, duration_ms: int = 0) -> dict:
    return {
        "agent_name": agent,
        "action": action,
        "alarm_id": state["alarm"].get("alarm_id"),
        "output": output,
        "duration_ms": duration_ms,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

# ─── AGENT 1: Supervisor ────────────────────────────────────────────────────────
def supervisor_agent(state: NOCState) -> NOCState:
    start = time.time()
    alarm = state["alarm"]
    severity = alarm.get("severity", "LOW")

    # Determine next action based on alarm
    if severity == "CRITICAL":
        next_action = "triage"
        hitl_required = False
    elif severity == "HIGH":
        next_action = "triage"
        hitl_required = False
    elif severity == "MEMO":
        next_action = "triage"
        hitl_required = False
    else:
        next_action = "triage"
        hitl_required = False

    event = log_event(state, "supervisor", "route_alarm",
        {"severity": severity, "next_action": next_action},
        int((time.time() - start) * 1000))

    return {**state, "next_action": next_action, "hitl_required": hitl_required,
            "agent_events": [event]}

# ─── AGENT 2: Alarm Triage ──────────────────────────────────────────────────────
async def triage_agent(state: NOCState) -> NOCState:
    start = time.time()
    alarm = state["alarm"]

    # Enrich alarm with NE and port details (from simulator data)
    ne_info = {
        "ne_id": alarm.get("ne_id"),
        "name": alarm.get("ne_name"),
        "type": alarm.get("ne_type"),
        "site": alarm.get("site"),
        "shelf": alarm.get("shelf"),
        "slot": alarm.get("slot"),
        "port": alarm.get("port"),
    }

    port_info = {
        "label": alarm.get("port_label"),
        "pm_data": alarm.get("pm_data", {}),
        "affected_circuits": alarm.get("affected_circuits", []),
    }

    event = log_event(state, "triage", "enrich_alarm",
        {"ne_info": ne_info, "port_info": port_info},
        int((time.time() - start) * 1000))

    return {**state, "ne_info": ne_info, "port_info": port_info,
            "next_action": "rca", "agent_events": [event]}

# ─── AGENT 3: RCA ───────────────────────────────────────────────────────────────
async def rca_agent(state: NOCState) -> NOCState:
    start = time.time()
    alarm = state["alarm"]
    ne_info = state.get("ne_info", {})
    port_info = state.get("port_info", {})

    llm = get_llm()

    prompt = f"""You are an expert NOC engineer specialising in SDH, OTN, and DWDM optical transport networks.

Analyse this alarm and provide root cause analysis:

ALARM DETAILS:
- Alarm Code: {alarm.get('alarm_code')}
- Alarm Type: {alarm.get('alarm_type')}
- Severity: {alarm.get('severity')}
- Description: {alarm.get('description')}
- Network Element: {ne_info.get('name')} ({ne_info.get('type')}) at {ne_info.get('site')}
- Port: Shelf {ne_info.get('shelf')} / Slot {ne_info.get('slot')} / Port {ne_info.get('port')}
- PM Data: {json.dumps(port_info.get('pm_data', {}))}
- Affected Circuits: {', '.join(port_info.get('affected_circuits', []))}

Respond in JSON only:
{{
  "root_cause": "concise root cause explanation",
  "confidence": 0.0-1.0,
  "requires_migration": true/false,
  "requires_mdt": true/false,
  "immediate_actions": ["action1", "action2"],
  "field_required": true/false,
  "estimated_resolution_minutes": 30
}}"""

    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        text = response.content.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        rca_data = json.loads(text)
    except Exception as e:
        log.error("rca_agent_error", error=str(e))
        rca_data = {
            "root_cause": f"Automated RCA failed — manual investigation required. Alarm: {alarm.get('alarm_code')} on {ne_info.get('name')}",
            "confidence": 0.3,
            "requires_migration": alarm.get("severity") == "CRITICAL",
            "requires_mdt": alarm.get("alarm_code") == "EQ-FAIL",
            "immediate_actions": ["Manual NMS inspection required", "Dispatch field team"],
            "field_required": True,
            "estimated_resolution_minutes": 60,
        }

    # Determine next action
    if rca_data.get("requires_migration") and alarm.get("severity") == "CRITICAL":
        next_action = "migration"
    elif rca_data.get("requires_mdt"):
        next_action = "mdt"
    else:
        next_action = "ticketing"

    event = log_event(state, "rca", "analyse_alarm", rca_data,
        int((time.time() - start) * 1000))

    return {**state, "rca_result": rca_data, "next_action": next_action,
            "agent_events": [event]}

# ─── AGENT 4: Migration ─────────────────────────────────────────────────────────
async def migration_agent(state: NOCState) -> NOCState:
    start = time.time()
    alarm = state["alarm"]
    ne_info = state.get("ne_info", {})
    port_info = state.get("port_info", {})

    llm = get_llm()

    prompt = f"""You are an expert NOC FDE planning emergency traffic migration on an optical transport network.

A CRITICAL alarm requires traffic migration to minimise outage.

ALARM: {alarm.get('alarm_code')} on {ne_info.get('name')} Port {ne_info.get('shelf')}/{ne_info.get('slot')}/{ne_info.get('port')}
AFFECTED CIRCUITS: {', '.join(port_info.get('affected_circuits', []))}
SITE: {ne_info.get('site')} | NE Type: {ne_info.get('type')}

Generate a migration plan. Assume there is a free port available on the same node (shelf {ne_info.get('shelf', 1)}, slot {ne_info.get('slot', 2)}, port {(int(ne_info.get('port') or 1) % 4) + 1}).

Respond in JSON only:
{{
  "source_port": "{ne_info.get('shelf')}/{ne_info.get('slot')}/{ne_info.get('port')}",
  "target_port": "{ne_info.get('shelf')}/{ne_info.get('slot', 2)}/{(int(ne_info.get('port') or 1) % 4) + 1}",
  "migration_steps": ["step1", "step2", "step3"],
  "estimated_restoration_minutes": 5,
  "risk_level": "LOW|MEDIUM|HIGH",
  "circuits_to_migrate": {json.dumps(port_info.get('affected_circuits', []))},
  "optical_budget_ok": true,
  "hitl_required": true
}}"""

    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        text = response.content.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        proposal = json.loads(text)
    except Exception as e:
        log.error("migration_agent_error", error=str(e))
        src_port = f"{ne_info.get('shelf')}/{ne_info.get('slot')}/{ne_info.get('port')}"
        tgt_slot = ne_info.get('slot', 2)
        tgt_port = (int(ne_info.get('port') or 1) % 4) + 1
        proposal = {
            "source_port": src_port,
            "target_port": f"{ne_info.get('shelf')}/{tgt_slot}/{tgt_port}",
            "migration_steps": [
                f"1. Verify target port {ne_info.get('shelf')}/{tgt_slot}/{tgt_port} is free and within optical budget",
                f"2. Reroute cross-connects from {src_port} to target port via NMS",
                "3. Verify traffic restoration — check BER < 1E-12",
                "4. Update JIRA ticket and notify stakeholders"
            ],
            "estimated_restoration_minutes": 8,
            "risk_level": "MEDIUM",
            "circuits_to_migrate": port_info.get("affected_circuits", []),
            "optical_budget_ok": True,
            "hitl_required": True,
        }

    proposal["migration_id"] = f"MIG-{uuid.uuid4().hex[:8].upper()}"
    proposal["alarm_id"] = alarm.get("alarm_id")
    proposal["status"] = "PROPOSED"

    event = log_event(state, "migration", "propose_migration", proposal,
        int((time.time() - start) * 1000))

    return {**state, "migration_proposal": proposal, "next_action": "ticketing",
            "hitl_required": True, "hitl_type": "MIGRATION",
            "agent_events": [event]}

# ─── AGENT 5: MDT ───────────────────────────────────────────────────────────────
async def mdt_agent(state: NOCState) -> NOCState:
    start = time.time()
    alarm = state["alarm"]
    ne_info = state.get("ne_info", {})
    rca = state.get("rca_result", {})

    mdt_number = f"MDT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    proposal = {
        "mdt_number": mdt_number,
        "alarm_id": alarm.get("alarm_id"),
        "ne_name": ne_info.get("name"),
        "maintenance_type": "CARD_RESET" if alarm.get("alarm_code") == "EQ-FAIL" else "PORT_RESET",
        "title": f"MDT: {alarm.get('alarm_code')} on {ne_info.get('name')} Slot {ne_info.get('slot')}",
        "description": f"Card/port reset required to resolve {alarm.get('alarm_code')} — {rca.get('root_cause', 'Hardware fault')}",
        "affected_services": alarm.get("affected_circuits", []),
        "estimated_duration_minutes": 15,
        "pre_check": "Confirm no live traffic on affected card ports",
        "commands": [
            f"# Via NMS CLI on {ne_info.get('name')}",
            f"reset card shelf {ne_info.get('shelf')} slot {ne_info.get('slot')}",
            "# Wait 3-8 minutes for card reboot",
            "# Verify all ports return to IS-NR state",
        ],
        "status": "REQUESTED",
        "hitl_required": True,
    }

    event = log_event(state, "mdt", "propose_mdt", proposal,
        int((time.time() - start) * 1000))

    return {**state, "mdt_proposal": proposal, "next_action": "ticketing",
            "hitl_required": True, "hitl_type": "MDT",
            "agent_events": [event]}

# ─── AGENT 6: Ticketing ─────────────────────────────────────────────────────────
async def ticketing_agent(state: NOCState) -> NOCState:
    start = time.time()
    alarm = state["alarm"]
    ne_info = state.get("ne_info", {})
    rca = state.get("rca_result", {})
    migration = state.get("migration_proposal")
    mdt = state.get("mdt_proposal")

    severity = alarm.get("severity", "MEMO")
    ticket_type_map = {"CRITICAL": "CRITICAL", "HIGH": "HIGH", "MEMO": "MEMO", "LOW": "MEMO"}
    ticket_type = ticket_type_map.get(severity, "MEMO")

    ticket_number = f"TT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    description_parts = [
        f"**Alarm:** {alarm.get('alarm_code')} — {alarm.get('alarm_type')}",
        f"**Node:** {ne_info.get('name')} ({ne_info.get('type')}) at {ne_info.get('site')}",
        f"**Port:** Shelf {ne_info.get('shelf')} / Slot {ne_info.get('slot')} / Port {ne_info.get('port')}",
        f"**Detected:** {alarm.get('detected_at')}",
        f"**PM Data:** {json.dumps(alarm.get('pm_data', {}))}",
        f"\n**AI Root Cause Analysis:**\n{rca.get('root_cause', 'N/A')}",
        f"**RCA Confidence:** {int(float(rca.get('confidence', 0)) * 100)}%",
    ]
    if migration:
        description_parts.append(f"\n**Migration Plan:** {migration.get('migration_id')} — {migration.get('source_port')} → {migration.get('target_port')} (Pending HITL Approval)")
    if mdt:
        description_parts.append(f"\n**MDT:** {mdt.get('mdt_number')} — {mdt.get('title')} (Pending HITL Approval)")

    ticket = {
        "ticket_number": ticket_number,
        "ticket_type": ticket_type,
        "alarm_id": alarm.get("alarm_id"),
        "title": f"[{severity}] {alarm.get('alarm_code')} — {ne_info.get('name')} Port {ne_info.get('port_label', '')}",
        "description": "\n".join(description_parts),
        "impact_statement": f"Traffic impact on circuits: {', '.join(alarm.get('affected_circuits', []))} at {ne_info.get('site')}",
        "assignee": "FDE-Team",
        "reporter": "AI-NOC-Agent",
        "status": "OPEN",
        "jira_simulated": True,
        "jira_key": f"NOC-{uuid.uuid4().hex[:4].upper()}",
    }

    # Simulate JIRA call (real integration via settings)
    if settings.JIRA_API_TOKEN and settings.JIRA_BASE_URL:
        ticket["jira_integration"] = "enabled"
    else:
        ticket["jira_integration"] = "mock"

    event = log_event(state, "ticketing", "create_ticket", ticket,
        int((time.time() - start) * 1000))

    return {**state, "ticket_result": ticket, "next_action": "notification",
            "agent_events": [event]}

# ─── AGENT 7: Notification ──────────────────────────────────────────────────────
async def notification_agent(state: NOCState) -> NOCState:
    start = time.time()
    alarm = state["alarm"]
    ne_info = state.get("ne_info", {})
    ticket = state.get("ticket_result", {})
    rca = state.get("rca_result", {})
    severity = alarm.get("severity", "MEMO")

    # Only send emails for CRITICAL and HIGH
    should_notify = severity in ("CRITICAL", "HIGH")

    email_body = f"""NOC ALERT — {severity} ALARM DETECTED

Network Element : {ne_info.get('name')} ({ne_info.get('type')})
Site            : {ne_info.get('site')}
Port            : Shelf {ne_info.get('shelf')} / Slot {ne_info.get('slot')} / Port {ne_info.get('port')}
Alarm           : {alarm.get('alarm_code')} — {alarm.get('alarm_type')}
Detected        : {alarm.get('detected_at')}
Ticket          : {ticket.get('ticket_number')} [{ticket.get('jira_key', 'N/A')}]
Circuits        : {', '.join(alarm.get('affected_circuits', []))}

AI Root Cause   : {rca.get('root_cause', 'Analysis pending')}
Confidence      : {int(float(rca.get('confidence', 0)) * 100)}%

Immediate Actions:
{chr(10).join(f'  • {a}' for a in rca.get('immediate_actions', []))}

Field Required  : {'YES — Dispatch immediately' if rca.get('field_required') else 'NO — Remote resolution possible'}
Est. Resolution : {rca.get('estimated_resolution_minutes', 60)} minutes

Next update in 30 minutes.

— NOC Agentic AI System | {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
"""

    notification = {
        "should_notify": should_notify,
        "severity": severity,
        "recipients": settings.EMAIL_MANAGEMENT.split(";") or ["management@example.com"],
        "subject": f"[{severity} ALARM] {alarm.get('alarm_code')} — {ne_info.get('name')} | {ticket.get('ticket_number')}",
        "body": email_body,
        "sent": False,
        "channel": "email",
    }

    # Simulate SendGrid send
    if should_notify and settings.SENDGRID_API_KEY:
        notification["sent"] = True
        notification["integration"] = "sendgrid"
    else:
        notification["integration"] = "mock"
        notification["sent"] = should_notify

    event = log_event(state, "notification", "send_alert", notification,
        int((time.time() - start) * 1000))

    return {**state, "notification_result": notification,
            "next_action": "complete", "agent_events": [event]}

# ─── Routing Functions ──────────────────────────────────────────────────────────
def route_after_supervisor(state: NOCState) -> str:
    return "triage"

def route_after_rca(state: NOCState) -> str:
    return state.get("next_action", "ticketing")

def route_after_ticketing(state: NOCState) -> str:
    return "notification"

def route_after_notification(state: NOCState) -> str:
    return END

# ─── Build Graph ────────────────────────────────────────────────────────────────
def build_noc_graph():
    graph = StateGraph(NOCState)

    graph.add_node("supervisor", supervisor_agent)
    graph.add_node("triage", triage_agent)
    graph.add_node("rca", rca_agent)
    graph.add_node("migration", migration_agent)
    graph.add_node("mdt", mdt_agent)
    graph.add_node("ticketing", ticketing_agent)
    graph.add_node("notification", notification_agent)

    graph.set_entry_point("supervisor")
    graph.add_edge("supervisor", "triage")
    graph.add_edge("triage", "rca")
    graph.add_conditional_edges("rca", route_after_rca, {
        "migration": "migration",
        "mdt": "mdt",
        "ticketing": "ticketing",
    })
    graph.add_edge("migration", "ticketing")
    graph.add_edge("mdt", "ticketing")
    graph.add_edge("ticketing", "notification")
    graph.add_edge("notification", END)

    return graph.compile()

# Singleton
_noc_graph = None

def get_noc_graph():
    global _noc_graph
    if _noc_graph is None:
        _noc_graph = build_noc_graph()
    return _noc_graph

async def process_alarm(alarm: dict) -> dict:
    """Entry point: run the full NOC agent pipeline on one alarm."""
    graph = get_noc_graph()
    initial_state: NOCState = {
        "alarm": alarm,
        "ne_info": None,
        "port_info": None,
        "rca_result": None,
        "migration_proposal": None,
        "mdt_proposal": None,
        "ticket_result": None,
        "notification_result": None,
        "agent_events": [],
        "next_action": "triage",
        "hitl_required": False,
        "hitl_type": None,
        "error": None,
    }
    try:
        result = await graph.ainvoke(initial_state)
        return result
    except Exception as e:
        log.error("pipeline_error", error=str(e), alarm_id=alarm.get("alarm_id"))
        return {**initial_state, "error": str(e)}
