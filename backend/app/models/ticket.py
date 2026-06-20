from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.db.database import Base
from datetime import datetime, timezone
import uuid


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    jira_key = Column(String(50), unique=True)
    alarm_id = Column(UUID(as_uuid=True), ForeignKey("alarms.id"))
    title = Column(String(500), nullable=False)
    description = Column(Text)
    priority = Column(String(20))
    status = Column(String(50), default="Open")
    assignee = Column(String(100))
    reporter = Column(String(100), default="NOC AI Agent")
    jira_url = Column(String(500))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime(timezone=True))
