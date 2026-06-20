"""
Mock NMS Simulator — generates realistic SDH/OTN/DWDM alarms for demo purposes.
In production, replace with real NMS NETCONF/REST adapters.
"""
import asyncio
import random
import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any
from app.core.config import settings

NODES = [
    {"name": "RIYADH-OTN-01", "ip": "10.1.1.1", "type": "OTN", "site": "Riyadh DC"},
    {"name": "JEDDAH-SDH-02", "ip": "10.1.1.2", "type": "SDH", "site": "Jeddah Hub"},
    {"name": "DAMMAM-DWDM-03", "ip": "10.1.1.3", "type": "DWDM", "site": "Dammam POP"},
    {"name": "MECCA-OTN-04", "ip": "10.1.1.4", "type": "OTN", "site": "Mecca NOC"},
    {"name": "MEDINA-SDH-05", "ip": "10.1.1.5", "type": "SDH", "site": "Medina Hub"},
    {"name": "KHOBAR-DWDM-06", "ip": "10.1.1.6", "type": "DWDM", "site": "Khobar DC"},
]

ALARM_TEMPLATES = [
    {
        "type": "LOS", "severity": "CRITICAL",
        "message": "Loss of Signal detected on optical port. Rx power below threshold.",
        "rx_power_range": (-35, -30), "ber_range": (1e-4, 1e-3),
    },
    {
        "type": "LOF", "severity": "CRITICAL",
        "message": "Loss of Frame on tributary port. Framing synchronisation failed.",
        "rx_power_range": (-28, -22), "ber_range": (1e-5, 1e-4),
    },
    {
        "type": "AIS", "severity": "HIGH",
        "message": "Alarm Indication Signal received — upstream failure propagating.",
        "rx_power_range": (-25, -18), "ber_range": (1e-6, 1e-5),
    },
    {
        "type": "BER_EXC", "severity": "HIGH",
        "message": "Bit Error Rate exceeds threshold. Signal degradation detected.",
        "rx_power_range": (-24, -18), "ber_range": (1e-5, 1e-4),
    },
    {
        "type": "EQ_FAIL", "severity": "CRITICAL",
        "message": "Equipment failure on line card. Hardware fault detected.",
        "rx_power_range": None, "ber_range": None,
    },
    {
        "type": "LOP", "severity": "HIGH",
        "message": "Loss of Pointer — SDH tributary sync issue.",
        "rx_power_range": (-22, -15), "ber_range": (1e-7, 1e-6),
    },
    {
        "type": "RDI", "severity": "HIGH",
        "message": "Remote Defect Indication — far-end node reporting defect.",
        "rx_power_range": (-20, -14), "ber_range": (1e-8, 1e-7),
    },
    {
        "type": "FAN_FAIL", "severity": "MEMO",
        "message": "Cooling fan failure detected in equipment shelf.",
        "rx_power_range": None, "ber_range": None,
    },
    {
        "type": "TEMP_HIGH", "severity": "MEMO",
        "message": "Equipment temperature exceeds operating threshold.",
        "rx_power_range": None, "ber_range": None,
    },
]

CIRCUIT_IDS = [
    "CID-00441", "CID-00442", "CID-00445", "CID-00891",
    "CID-01002", "CID-01003", "CID-01456", "CID-02001",
]


def generate_alarm() -> Dict[str, Any]:
    node = random.choice(NODES)
    template = random.choice(ALARM_TEMPLATES)
    shelf = random.randint(1, 4)
    slot = random.randint(1, 16)
    port = random.randint(1, 8)
    circuits = random.sample(CIRCUIT_IDS, k=random.randint(1, 3))

    alarm = {
        "id": str(uuid.uuid4()),
        "alarm_type": template["type"],
        "severity": template["severity"],
        "status": "ACTIVE",
        "node_name": node["name"],
        "node_ip": node["ip"],
        "shelf": shelf,
        "slot": slot,
        "port": port,
        "wavelength": f"CH-{random.randint(1, 96)}" if node["type"] == "DWDM" else None,
        "circuit_ids": json.dumps(circuits),
        "alarm_message": template["message"],
        "rx_power": round(random.uniform(*template["rx_power_range"]), 2) if template["rx_power_range"] else None,
        "ber_value": float(f"{random.uniform(*template['ber_range']):.2e}") if template["ber_range"] else None,
        "osnr": round(random.uniform(12.0, 28.0), 1) if node["type"] == "DWDM" else None,
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "nms_source": "SIMULATOR",
        "equipment_type": node["type"],
    }
    return alarm


class NMSSimulator:
    def __init__(self):
        self._running = False
        self._callbacks = []

    def add_callback(self, cb):
        self._callbacks.append(cb)

    async def start(self):
        self._running = True
        while self._running:
            alarm = generate_alarm()
            for cb in self._callbacks:
                try:
                    await cb(alarm)
                except Exception as e:
                    print(f"NMS callback error: {e}")
            await asyncio.sleep(settings.NMS_ALARM_INTERVAL_SECONDS)

    def stop(self):
        self._running = False


nms_simulator = NMSSimulator()
