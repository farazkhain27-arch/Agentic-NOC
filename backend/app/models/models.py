from sqlalchemy import Column, String, Integer, Boolean, Text, Numeric, DateTime, ForeignKey, JSON, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.database import Base
from datetime import datetime
import uuid
import enum

class AlarmSeverity(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEMO = "MEMO"
    LOW = "LOW"

class AlarmStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    SUPPRESSED = "SUPPRESSED"

class TicketStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    PENDING_FIELD = "PENDING_FIELD"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"

class TicketType(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEMO = "MEMO"
    CHANGE = "CHANGE"

class MDTStatus(str, enum.Enum):
    REQUESTED = "REQUESTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class MigrationStatus(str, enum.Enum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class NetworkElement(Base):
    __tablename__ = "network_elements"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ne_id = Column(String(64), unique=True, nullable=False)
    name = Column(String(128), nullable=False)
    ip_address = Column(String(45))
    ne_type = Column(String(32), nullable=False)
    vendor = Column(String(64))
    site_name = Column(String(128))
    region = Column(String(64))
    status = Column(String(32), default="UP")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    alarms = relationship("Alarm", back_populates="network_element")
    ports = relationship("Port", back_populates="network_element")

class Port(Base):
    __tablename__ = "ports"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ne_id = Column(UUID(as_uuid=True), ForeignKey("network_elements.id"))
    shelf = Column(Integer, nullable=False)
    slot = Column(Integer, nullable=False)
    port = Column(Integer, nullable=False)
    port_label = Column(String(64))
    port_type = Column(String(32))
    speed_gbps = Column(Numeric(10, 2))
    status = Column(String(32), default="UP")
    is_free = Column(Boolean, default=False)
    circuit_id = Column(String(128))
    rx_power_dbm = Column(Numeric(8, 2))
    tx_power_dbm = Column(Numeric(8, 2))
    network_element = relationship("NetworkElement", back_populates="ports")

class Alarm(Base):
    __tablename__ = "alarms"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alarm_id = Column(String(128), unique=True, nullable=False)
    ne_id = Column(UUID(as_uuid=True), ForeignKey("network_elements.id"))
    port_id = Column(UUID(as_uuid=True), ForeignKey("ports.id"), nullable=True)
    alarm_code = Column(String(64), nullable=False)
    alarm_type = Column(String(64))
    severity = Column(SAEnum(AlarmSeverity), nullable=False)
    status = Column(SAEnum(AlarmStatus), default=AlarmStatus.ACTIVE)
    description = Column(Text)
    affected_circuits = Column(JSONB, default=list)
    pm_data = Column(JSONB, default=dict)
    raw_nms_data = Column(JSONB, default=dict)
    detected_at = Column(DateTime, default=datetime.utcnow)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    ticket_id = Column(String(64), nullable=True)
    agent_rca = Column(Text, nullable=True)
    agent_confidence = Column(Numeric(5, 2), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    network_element = relationship("NetworkElement", back_populates="alarms")

class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_number = Column(String(64), unique=True, nullable=False)
    jira_key = Column(String(64), nullable=True)
    alarm_id = Column(UUID(as_uuid=True), ForeignKey("alarms.id"), nullable=True)
    ticket_type = Column(SAEnum(TicketType), nullable=False)
    status = Column(SAEnum(TicketStatus), default=TicketStatus.OPEN)
    title = Column(String(256), nullable=False)
    description = Column(Text)
    impact_statement = Column(Text)
    rfo = Column(Text, nullable=True)
    resolution = Column(Text, nullable=True)
    assignee = Column(String(128))
    reporter = Column(String(128))
    steps_taken = Column(JSONB, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

class Migration(Base):
    __tablename__ = "migrations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id"), nullable=True)
    alarm_id = Column(UUID(as_uuid=True), ForeignKey("alarms.id"), nullable=True)
    source_port_id = Column(UUID(as_uuid=True), ForeignKey("ports.id"), nullable=True)
    target_port_id = Column(UUID(as_uuid=True), ForeignKey("ports.id"), nullable=True)
    affected_circuits = Column(JSONB, default=list)
    migration_plan = Column(Text)
    status = Column(SAEnum(MigrationStatus), default=MigrationStatus.PROPOSED)
    proposed_by = Column(String(128), default="AI-Agent")
    approved_by = Column(String(128), nullable=True)
    approval_notes = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    pre_migration_pm = Column(JSONB, default=dict)
    post_migration_pm = Column(JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MDT(Base):
    __tablename__ = "mdts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mdt_number = Column(String(64), unique=True, nullable=False)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id"), nullable=True)
    alarm_id = Column(UUID(as_uuid=True), ForeignKey("alarms.id"), nullable=True)
    ne_id = Column(UUID(as_uuid=True), ForeignKey("network_elements.id"), nullable=True)
    port_id = Column(UUID(as_uuid=True), ForeignKey("ports.id"), nullable=True)
    title = Column(String(256), nullable=False)
    description = Column(Text)
    maintenance_type = Column(String(64))
    affected_services = Column(JSONB, default=list)
    status = Column(SAEnum(MDTStatus), default=MDTStatus.REQUESTED)
    requested_by = Column(String(128))
    approved_by = Column(String(128), nullable=True)
    approval_notes = Column(Text, nullable=True)
    scheduled_start = Column(DateTime, nullable=True)
    scheduled_end = Column(DateTime, nullable=True)
    actual_start = Column(DateTime, nullable=True)
    actual_end = Column(DateTime, nullable=True)
    commands_executed = Column(JSONB, default=list)
    post_mdt_verification = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AgentEvent(Base):
    __tablename__ = "agent_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alarm_id = Column(UUID(as_uuid=True), ForeignKey("alarms.id"), nullable=True)
    agent_name = Column(String(64), nullable=False)
    action = Column(String(128), nullable=False)
    input_data = Column(JSONB, default=dict)
    output_data = Column(JSONB, default=dict)
    langsmith_run_id = Column(String(128), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class DailyReport(Base):
    __tablename__ = "daily_reports"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_date = Column(String(32), unique=True, nullable=False)
    total_alarms = Column(Integer, default=0)
    critical_alarms = Column(Integer, default=0)
    high_alarms = Column(Integer, default=0)
    memo_alarms = Column(Integer, default=0)
    tickets_opened = Column(Integer, default=0)
    tickets_resolved = Column(Integer, default=0)
    migrations_performed = Column(Integer, default=0)
    mdts_performed = Column(Integer, default=0)
    avg_mttr_minutes = Column(Numeric(10, 2), nullable=True)
    top_issues = Column(JSONB, default=list)
    report_content = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
