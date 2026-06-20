"""Shared state schema for the NOC LangGraph multi-agent pipeline."""
from typing import TypedDict, Optional, List, Dict, Any, Annotated
from langgraph.graph.message import add_messages


class NOCState(TypedDict):
    # Input alarm data
    alarm: Dict[str, Any]

    # Agent outputs
    messages: Annotated[List, add_messages]
    triage_result: Optional[Dict[str, Any]]
    rca_result: Optional[Dict[str, Any]]
    migration_plan: Optional[Dict[str, Any]]
    mdt_plan: Optional[Dict[str, Any]]
    ticket_result: Optional[Dict[str, Any]]
    notification_result: Optional[Dict[str, Any]]
    report_data: Optional[Dict[str, Any]]

    # Control flow
    requires_migration: bool
    requires_mdt: bool
    requires_human_approval: bool
    human_approved: Optional[bool]
    approval_type: Optional[str]  # "migration" | "mdt"
    severity_level: Optional[str]
    error: Optional[str]
    processing_complete: bool
