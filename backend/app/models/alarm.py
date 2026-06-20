from sqlalchemy import Column, String, DateTime, Text, Float, Enum as SAEnum, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from app.db.database import Base
from datetime import datetime, timezone
import uuid
import enum


class AlarmSeverity(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEMO = "MEMO"
    INFO = "INFO"


class AlarmStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    SUPPRESSED = "SUPPRESSED"


class AlarmType(str, enum.Enum):
    LOS = "LOS"
    LOF = "LOF"
    AIS = "AIS"
    BER_EXC = "BER_EXC"
    LOP = "LOP"
    EQ_FAIL = "EQ_FAIL"
    RDI = "RDI"
    PWR_FAIL = "PWR_FAIL"
    TEMP_HIGH = "TEMP_HIGH"
    FAN_FAIL = "FAN_FAIL"


class Alarm(Base):
    __tablename__ = "alarms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alarm_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    status = Column(String(20), default="ACTIVE")
    node_name = Column(String(100), nullable=False)
    node_ip = Column(String(50))
    shelf = Column(Integer)
    slot = Column(Integer)
    port = Column(Integer)
    wavelength = Column(String(20))
    circuit_ids = Column(Text)  # JSON array as string
    alarm_message = Column(Text)
    rx_power = Column(Float)
    ber_value = Column(Float)
    osnr = Column(Float)
    detected_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    acknowledged_at = Column(DateTime(timezone=True))
    resolved_at = Column(DateTime(timezone=True))
    jira_ticket_id = Column(String(50))
    rca_summary = Column(Text)
    acknowledged_by = Column(String(100))
    nms_source = Column(String(50), default="SIMULATOR")
    equipment_type = Column(String(20), default="OTN")  # SDH, OTN, DWDM
