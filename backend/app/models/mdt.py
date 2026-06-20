from sqlalchemy import Column, String, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.db.database import Base
from datetime import datetime, timezone
import uuid


class MDTRequest(Base):
    __tablename__ = "mdt_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alarm_id = Column(String(100))
    node_name = Column(String(100), nullable=False)
    shelf = Column(String(20))
    slot = Column(String(20))
    reason = Column(Text, nullable=False)
    requested_by = Column(String(100))
    approved_by = Column(String(100))
    status = Column(String(30), default="PENDING")  # PENDING, APPROVED, REJECTED, COMPLETED
    scheduled_start = Column(DateTime(timezone=True))
    scheduled_end = Column(DateTime(timezone=True))
    actual_start = Column(DateTime(timezone=True))
    actual_end = Column(DateTime(timezone=True))
    affected_circuits = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    jira_ticket_id = Column(String(50))
