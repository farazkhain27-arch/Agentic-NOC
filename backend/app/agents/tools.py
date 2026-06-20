"""LangChain tools available to NOC agents."""
import json
import random
from typing import Optional
from langchain_core.tools import tool
from datetime import datetime, timezone


@tool
def query_circuit_database(node_name: str, port: str) -> str:
    """Query the circuit database to find circuits on a specific node/port."""
    # In production: query real topology DB
    circuits = [
        {"id": f"CID-{random.randint(10000,99999)}", "customer": "Saudi Telecom Co", "bandwidth": "10G", "protection": "1+1"},
        {"id": f"CID-{random.randint(10000,99999)}", "customer": "STC Business", "bandwidth": "1G", "protection": "unprotected"},
    ]
    return json.dumps({"node": node_name, "port": port, "circuits": circuits})


@tool
def find_free_ports(node_name: str, bandwidth_required: str = "10G") -> str:
    """Find available free ports on the same route for traffic migration."""
    # In production: query NMS capacity database
    free_ports = [
        {"node": node_name, "shelf": 2, "slot": 4, "port": 3, "bandwidth": "100G", "utilisation": "0%"},
        {"node": node_name, "shelf": 1, "slot": 8, "port": 5, "bandwidth": "100G", "utilisation": "15%"},
    ]
    return json.dumps({"available_ports": free_ports, "recommended": free_ports[0]})


@tool
def get_optical_pm_data(node_name: str, shelf: int, slot: int, port: int) -> str:
    """Retrieve current optical performance monitoring data for a port."""
    pm_data = {
        "node": node_name, "shelf": shelf, "slot": slot, "port": port,
        "rx_power_dbm": round(random.uniform(-25, -12), 2),
        "tx_power_dbm": round(random.uniform(-5, 2), 2),
        "ber": f"{random.uniform(1e-12, 1e-9):.2e}",
        "osnr_db": round(random.uniform(18, 32), 1),
        "q_factor_db": round(random.uniform(8, 20), 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return json.dumps(pm_data)


@tool
def get_alarm_history(node_name: str, hours: int = 24) -> str:
    """Get alarm history for a node over the past N hours."""
    history = [
        {"alarm_type": "BER_EXC", "severity": "HIGH", "occurred_at": "2024-01-15T10:22:00Z", "duration_minutes": 45},
        {"alarm_type": "LOS", "severity": "CRITICAL", "occurred_at": "2024-01-14T03:15:00Z", "duration_minutes": 120},
    ]
    return json.dumps({"node": node_name, "period_hours": hours, "alarms": history})


@tool
def check_upstream_downstream(node_name: str) -> str:
    """Check status of upstream and downstream nodes to correlate alarms."""
    nodes_info = {
        "upstream": {"name": f"UPSTREAM-OF-{node_name}", "status": "NORMAL", "active_alarms": 0},
        "downstream": {"name": f"DOWNSTREAM-OF-{node_name}", "status": "DEGRADED", "active_alarms": 2},
        "analysis": "Downstream node showing degradation — possible fibre issue between nodes."
    }
    return json.dumps(nodes_info)


@tool
def validate_migration_route(source_port: str, target_port: str) -> str:
    """Validate that a proposed migration route has sufficient optical budget."""
    validation = {
        "source_port": source_port,
        "target_port": target_port,
        "optical_budget_ok": True,
        "estimated_loss_db": round(random.uniform(8, 18), 1),
        "margin_db": round(random.uniform(3, 8), 1),
        "route_distance_km": round(random.uniform(50, 500), 0),
        "recommendation": "Route validated. Sufficient optical margin for migration."
    }
    return json.dumps(validation)


NOC_TOOLS = [
    query_circuit_database,
    find_free_ports,
    get_optical_pm_data,
    get_alarm_history,
    check_upstream_downstream,
    validate_migration_route,
]
