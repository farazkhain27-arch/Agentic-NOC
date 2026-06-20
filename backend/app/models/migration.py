from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from app.db.database import Base
from datetime import datetime, timezone
import uuid


class MigrationRequest(Base):
    __tablename__ = "migration_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alarm_id = Column(String(100))
    source_node = Column(String(100))
    source_port = Column(String(50))
    target_node = Column(String(100))
    target_port = Column(String(50))
    affected_circuits = Column(Text)
    status = Column(String(30), default="PENDING_APPROVAL")
    requested_by = Column(String(100), default="AI Migration Agent")
    approved_by = Column(String(100))
    reason = Column(Text)
    estimated_restoration_minutes = Column(String(20))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    executed_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    notes = Column(Text)
