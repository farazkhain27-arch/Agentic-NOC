"""
NOC Multi-Agent LangGraph Pipeline
8 agents: Supervisor → Triage → RCA → Migration/MDT → Ticketing → Notification → Report
"""
import json
import os
from typing import Literal
from datetime import datetime, timezone

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.agents.state import NOCState
from app.agents.tools import NOC_TOOLS
from app.core.config import settings

# ── LLM setup ──────────────────────────────────────────────────────────────────
llm = ChatAnthropic(
    model=settings.CLAUDE_MODEL,
    anthropic_api_key=settings.ANTHROPIC_API_KEY,
    max_tokens=2048,
)
llm_with_tools = llm.bind_tools(NOC_TOOLS)

# ── Helper ─────────────────────────────────────────────────────────────────────
def _invoke(system: str, user: str) -> str:
    resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    return resp.content if hasattr(resp, "content") else str(resp)


# ── Agent Nodes ────────────────────────────────────────────────────────────────

def supervisor_agent(state: NOCState) -> NOCState:
    """Classifies alarm and routes to appropriate sub-agents."""
    alarm = state["alarm"]
    severity = alarm.get("severity", "INFO")

    prompt = f"""You are the NOC Supervisor Agent. Analyse this alarm and determine:
1. Overall severity classification
2. Whether emergency traffic migration is needed
3. Whether an MDT (card reset) is needed
4. Whether human approval is required before action

Alarm: {json.dumps(alarm, indent=2)}

Respond in JSON:
{{"severity": "CRITICAL|HIGH|MEMO|INFO", "requires_migration": true|false, "requires_mdt": true|false, "requires_human_approval": true|false, "reasoning": "brief explanation"}}"""

    try:
        result = _invoke("You are a senior NOC supervisor AI for optical transport networks (SDH/OTN/DWDM).", prompt)
        # Extract JSON from response
        start = result.find("{")
        end = result.rfind("}") + 1
        parsed = json.loads(result[start:end])
    except Exception:
        parsed = {
            "severity": severity,
            "requires_migration": severity == "CRITICAL" and alarm.get("alarm_type") in ["LOS", "LOF", "EQ_FAIL"],
            "requires_mdt": alarm.get("alarm_type") in ["EQ_FAIL"],
            "requires_human_approval": severity == "CRITICAL",
            "reasoning": "Fallback classification based on alarm type and severity."
        }

    return {
        **state,
        "severity_level": parsed.get("severity", severity),
        "requires_migration": parsed.get("requires_migration", False),
        "requires_mdt": parsed.get("requires_mdt", False),
        "requires_human_approval": parsed.get("requires_human_approval", False),
        "messages": [HumanMessage(content=f"Supervisor: {parsed.get('reasoning', '')}")]
    }


def triage_agent(state: NOCState) -> NOCState:
    """Enriches alarm with topology context and affected circuit details."""
    alarm = state["alarm"]

    prompt = f"""You are the NOC Triage Agent. Analyse this alarm and provide a structured triage report.

Alarm data: {json.dumps(alarm, indent=2)}

Provide triage in JSON format:
{{
  "alarm_summary": "one-line summary",
  "affected_equipment": "description of affected hardware",
  "estimated_impact": "description of service impact",
  "immediate_actions": ["action 1", "action 2"],
  "escalation_needed": true|false,
  "triage_confidence": 0.0-1.0
}}"""

    try:
        result = _invoke("You are an expert NOC triage engineer for optical transport networks.", prompt)
        start, end = result.find("{"), result.rfind("}") + 1
        triage = json.loads(result[start:end])
    except Exception:
        triage = {
            "alarm_summary": f"{alarm.get('alarm_type')} on {alarm.get('node_name')} port {alarm.get('shelf')}/{alarm.get('slot')}/{alarm.get('port')}",
            "affected_equipment": f"Node: {alarm.get('node_name')}, Shelf {alarm.get('shelf')}, Slot {alarm.get('slot')}, Port {alarm.get('port')}",
            "estimated_impact": "Service impact assessment pending.",
            "immediate_actions": ["Collect alarm logs", "Check upstream/downstream nodes", "Notify field team"],
            "escalation_needed": alarm.get("severity") == "CRITICAL",
            "triage_confidence": 0.7,
        }

    return {**state, "triage_result": triage, "messages": [HumanMessage(content=f"Triage complete: {triage.get('alarm_summary')}")]}


def rca_agent(state: NOCState) -> NOCState:
    """Performs root cause analysis using alarm data and historical patterns."""
    alarm = state["alarm"]
    triage = state.get("triage_result", {})

    prompt = f"""You are the NOC Root Cause Analysis Agent. Perform RCA on this alarm.

Alarm: {json.dumps(alarm, indent=2)}
Triage: {json.dumps(triage, indent=2)}

Provide RCA in JSON:
{{
  "probable_root_cause": "most likely root cause",
  "contributing_factors": ["factor 1", "factor 2"],
  "confidence": 0.0-1.0,
  "evidence": ["evidence point 1", "evidence point 2"],
  "recommended_resolution": "step-by-step resolution",
  "prevention_recommendation": "how to prevent recurrence",
  "rfo_category": "Fibre|Hardware|Software|Config|External|Unknown"
}}"""

    try:
        result = _invoke("You are an expert RCA engineer for SDH/OTN/DWDM optical networks.", prompt)
        start, end = result.find("{"), result.rfind("}") + 1
        rca = json.loads(result[start:end])
    except Exception:
        alarm_type = alarm.get("alarm_type", "UNKNOWN")
        rca = {
            "probable_root_cause": f"Hardware or fibre issue causing {alarm_type} on optical port.",
            "contributing_factors": ["Possible fibre degradation", "Hardware ageing"],
            "confidence": 0.65,
            "evidence": [f"Alarm type: {alarm_type}", f"Severity: {alarm.get('severity')}"],
            "recommended_resolution": "Dispatch field engineer to inspect fibre and hardware.",
            "prevention_recommendation": "Schedule periodic fibre OTDR testing and hardware health checks.",
            "rfo_category": "Unknown"
        }

    return {**state, "rca_result": rca, "messages": [HumanMessage(content=f"RCA: {rca.get('probable_root_cause')}")]}


def migration_agent(state: NOCState) -> NOCState:
    """Proposes traffic migration plan when required."""
    if not state.get("requires_migration"):
        return state

    alarm = state["alarm"]
    prompt = f"""You are the NOC Traffic Migration Agent. Create a migration plan for this failed port.

Alarm: {json.dumps(alarm, indent=2)}

Provide migration plan in JSON:
{{
  "source_port": "shelf/slot/port description",
  "target_port": "recommended target port",
  "target_node": "node name",
  "affected_circuits": ["circuit ids"],
  "migration_steps": ["step 1", "step 2", "step 3"],
  "estimated_restoration_minutes": 5,
  "risk_level": "LOW|MEDIUM|HIGH",
  "optical_budget_margin_db": 5.0,
  "approval_required": true
}}"""

    try:
        result = _invoke("You are an expert NOC migration engineer for optical transport networks.", prompt)
        start, end = result.find("{"), result.rfind("}") + 1
        plan = json.loads(result[start:end])
    except Exception:
        plan = {
            "source_port": f"Shelf {alarm.get('shelf')}/Slot {alarm.get('slot')}/Port {alarm.get('port')}",
            "target_port": f"Shelf 2/Slot 4/Port 3",
            "target_node": alarm.get("node_name"),
            "affected_circuits": json.loads(alarm.get("circuit_ids", "[]")),
            "migration_steps": [
                "Verify target port optical budget margin",
                "Coordinate with customer for brief service interruption",
                "Execute cross-connect re-route via NMS",
                "Verify traffic restoration on target port",
                "Update circuit database with new port assignment"
            ],
            "estimated_restoration_minutes": 8,
            "risk_level": "MEDIUM",
            "optical_budget_margin_db": 5.5,
            "approval_required": True
        }

    return {
        **state,
        "migration_plan": plan,
        "requires_human_approval": True,
        "approval_type": "migration",
        "messages": [HumanMessage(content=f"Migration plan ready: {plan.get('source_port')} → {plan.get('target_port')}")]
    }


def mdt_agent(state: NOCState) -> NOCState:
    """Prepares MDT request for card reset approval."""
    if not state.get("requires_mdt"):
        return state

    alarm = state["alarm"]
    prompt = f"""You are the NOC MDT Agent. Prepare a Maintenance Down Time request for card reset.

Alarm: {json.dumps(alarm, indent=2)}

Provide MDT request in JSON:
{{
  "mdt_title": "MDT request title",
  "reason": "detailed reason for MDT",
  "affected_equipment": "card/shelf/slot description",
  "affected_circuits": ["circuit ids"],
  "estimated_downtime_minutes": 10,
  "pre_checks": ["check 1", "check 2"],
  "reset_procedure": ["step 1", "step 2"],
  "post_checks": ["verify 1", "verify 2"],
  "risk_assessment": "LOW|MEDIUM|HIGH",
  "rollback_plan": "what to do if reset fails"
}}"""

    try:
        result = _invoke("You are an expert NOC MDT coordinator for optical transport networks.", prompt)
        start, end = result.find("{"), result.rfind("}") + 1
        mdt = json.loads(result[start:end])
    except Exception:
        mdt = {
            "mdt_title": f"Card Reset MDT — {alarm.get('node_name')} Shelf {alarm.get('shelf')} Slot {alarm.get('slot')}",
            "reason": f"Equipment failure alarm ({alarm.get('alarm_type')}) — card reset required to restore normal operation.",
            "affected_equipment": f"Node: {alarm.get('node_name')}, Shelf {alarm.get('shelf')}, Slot {alarm.get('slot')}",
            "affected_circuits": json.loads(alarm.get("circuit_ids", "[]")),
            "estimated_downtime_minutes": 8,
            "pre_checks": ["Migrate live traffic from affected card", "Confirm spare capacity available", "Notify customers"],
            "reset_procedure": ["Log into NMS CLI", "Execute card reset command", "Monitor card reboot (3-8 min)"],
            "post_checks": ["Verify all ports return to normal", "Confirm PM values within expected range", "Restore migrated traffic"],
            "risk_assessment": "MEDIUM",
            "rollback_plan": "If card fails to recover, initiate hardware replacement RMA with vendor TAC."
        }

    return {
        **state,
        "mdt_plan": mdt,
        "requires_human_approval": True,
        "approval_type": "mdt",
        "messages": [HumanMessage(content=f"MDT prepared: {mdt.get('mdt_title')}")]
    }


def ticketing_agent(state: NOCState) -> NOCState:
    """Creates JIRA ticket with full alarm context."""
    alarm = state["alarm"]
    triage = state.get("triage_result", {})
    rca = state.get("rca_result", {})
    severity = state.get("severity_level", alarm.get("severity", "HIGH"))

    priority_map = {"CRITICAL": "P1 - Critical", "HIGH": "P2 - High", "MEMO": "P3 - Memo", "INFO": "P4 - Info"}
    priority = priority_map.get(severity, "P2 - High")

    title = f"[{severity}] {alarm.get('alarm_type')} — {alarm.get('node_name')} | Port {alarm.get('shelf')}/{alarm.get('slot')}/{alarm.get('port')}"
    description = f"""h2. Alarm Details
*Alarm Type:* {alarm.get('alarm_type')}
*Severity:* {severity}
*Node:* {alarm.get('node_name')} ({alarm.get('node_ip')})
*Port:* Shelf {alarm.get('shelf')} / Slot {alarm.get('slot')} / Port {alarm.get('port')}
*Equipment:* {alarm.get('equipment_type')}
*Detected At:* {alarm.get('detected_at')}

h2. Impact Assessment
{triage.get('estimated_impact', 'Under investigation')}

h2. Affected Circuits
{alarm.get('circuit_ids', '[]')}

h2. Optical PM Values
* Rx Power: {alarm.get('rx_power')} dBm
* BER: {alarm.get('ber_value')}
* OSNR: {alarm.get('osnr')} dB

h2. Root Cause Analysis
*Probable Cause:* {rca.get('probable_root_cause', 'Under investigation')}
*Confidence:* {int(float(rca.get('confidence', 0.7)) * 100)}%
*RFO Category:* {rca.get('rfo_category', 'Unknown')}

h2. Recommended Actions
{rca.get('recommended_resolution', 'Field investigation required')}

h2. Actions Taken
* AI Agent detected and triaged alarm automatically
* Ticket created at {datetime.now(timezone.utc).isoformat()}
"""

    ticket_data = {
        "title": title,
        "description": description,
        "priority": priority,
        "alarm_id": alarm.get("id"),
        "status": "Open",
        "reporter": "NOC AI Agent",
        "jira_key": f"NOC-{abs(hash(alarm.get('id', ''))) % 9000 + 1000}",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # In production: POST to JIRA REST API
    return {**state, "ticket_result": ticket_data, "messages": [HumanMessage(content=f"Ticket created: {ticket_data['jira_key']}")]}


def notification_agent(state: NOCState) -> NOCState:
    """Sends email notifications to management based on severity."""
    alarm = state["alarm"]
    severity = state.get("severity_level", "HIGH")
    ticket = state.get("ticket_result", {})
    rca = state.get("rca_result", {})

    if severity not in ["CRITICAL", "HIGH"]:
        return {**state, "notification_result": {"sent": False, "reason": "Severity below notification threshold"}}

    subject = f"[{severity} ALARM] {alarm.get('alarm_type')} — {alarm.get('node_name')} — {ticket.get('jira_key', 'TT-PENDING')}"
    body = f"""NOC AUTOMATED ALERT — {severity}

Alarm Type    : {alarm.get('alarm_type')}
Node          : {alarm.get('node_name')} ({alarm.get('node_ip')})
Port          : Shelf {alarm.get('shelf')} / Slot {alarm.get('slot')} / Port {alarm.get('port')}
Equipment     : {alarm.get('equipment_type')}
Detected At   : {alarm.get('detected_at')}
JIRA Ticket   : {ticket.get('jira_key', 'PENDING')}

ROOT CAUSE ANALYSIS
Probable Cause: {rca.get('probable_root_cause', 'Under investigation')}
Confidence    : {int(float(rca.get('confidence', 0.7)) * 100)}%

RECOMMENDED ACTION
{rca.get('recommended_resolution', 'Field team dispatch required')}

This alert was generated automatically by the NOC Agentic AI System.
Next update will follow in 30 minutes or upon status change.

NOC Operations | Powered by LangGraph + Claude
"""

    notification_result = {
        "sent": True,
        "subject": subject,
        "body": body,
        "recipients": settings.EMAIL_MANAGEMENT.split(";"),
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }

    # In production: call SendGrid API here
    return {**state, "notification_result": notification_result, "messages": [HumanMessage(content=f"Email notification sent for {severity} alarm")]}


def report_agent(state: NOCState) -> NOCState:
    """Compiles final processing report for the alarm."""
    return {
        **state,
        "report_data": {
            "alarm_id": state["alarm"].get("id"),
            "severity": state.get("severity_level"),
            "triage_summary": state.get("triage_result", {}).get("alarm_summary"),
            "rca_cause": state.get("rca_result", {}).get("probable_root_cause"),
            "ticket_key": state.get("ticket_result", {}).get("jira_key"),
            "notification_sent": state.get("notification_result", {}).get("sent", False),
            "migration_required": state.get("requires_migration", False),
            "mdt_required": state.get("requires_mdt", False),
            "human_approval_pending": state.get("requires_human_approval", False) and state.get("human_approved") is None,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        },
        "processing_complete": True,
        "messages": [HumanMessage(content="NOC pipeline processing complete.")]
    }


# ── Routing functions ──────────────────────────────────────────────────────────

def route_after_supervisor(state: NOCState) -> Literal["triage"]:
    return "triage"

def route_after_rca(state: NOCState) -> Literal["migration", "mdt", "ticketing"]:
    if state.get("requires_migration"):
        return "migration"
    if state.get("requires_mdt"):
        return "mdt"
    return "ticketing"

def route_after_migration(state: NOCState) -> Literal["ticketing"]:
    return "ticketing"

def route_after_mdt(state: NOCState) -> Literal["ticketing"]:
    return "ticketing"


# ── Build graph ────────────────────────────────────────────────────────────────

def build_noc_graph():
    builder = StateGraph(NOCState)

    builder.add_node("supervisor", supervisor_agent)
    builder.add_node("triage", triage_agent)
    builder.add_node("rca", rca_agent)
    builder.add_node("migration", migration_agent)
    builder.add_node("mdt", mdt_agent)
    builder.add_node("ticketing", ticketing_agent)
    builder.add_node("notification", notification_agent)
    builder.add_node("report", report_agent)

    builder.set_entry_point("supervisor")
    builder.add_edge("supervisor", "triage")
    builder.add_edge("triage", "rca")
    builder.add_conditional_edges("rca", route_after_rca, {"migration": "migration", "mdt": "mdt", "ticketing": "ticketing"})
    builder.add_edge("migration", "ticketing")
    builder.add_edge("mdt", "ticketing")
    builder.add_edge("ticketing", "notification")
    builder.add_edge("notification", "report")
    builder.add_edge("report", END)

    memory = MemorySaver()
    return builder.compile(checkpointer=memory)


noc_graph = build_noc_graph()
