from datetime import datetime, timezone
from enum import StrEnum
from sqlalchemy import JSON, DateTime, Integer, String, Text, UniqueConstraint, Index, CheckConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase): pass
class Status(StrEnum):
    PENDING="PENDING"; DELIVERING="DELIVERING"; RETRY_WAITING="RETRY_WAITING"; DELIVERED="DELIVERED"; FAILED="FAILED"

class NotificationRow(Base):
    __tablename__="notifications"
    __table_args__=(UniqueConstraint("provider","idempotency_key"),CheckConstraint("attempt_count >= 0"),CheckConstraint("max_attempts >= 1"),Index("poll_idx","status","next_attempt_at","created_at"),Index("lease_idx","status","lease_until"))
    id: Mapped[str]=mapped_column(String(64),primary_key=True)
    provider: Mapped[str]=mapped_column(String(128),nullable=False)
    event_type: Mapped[str]=mapped_column(String(128),nullable=False)
    target_url: Mapped[str]=mapped_column(Text,nullable=False)
    http_method: Mapped[str]=mapped_column(String(16),nullable=False,default="POST")
    headers_json: Mapped[dict]=mapped_column(JSON,nullable=False,default=dict)
    body_json: Mapped[object]=mapped_column(JSON,nullable=False)
    idempotency_key: Mapped[str|None]=mapped_column(String(256),nullable=True)
    request_digest: Mapped[str]=mapped_column(String(64),nullable=False)
    status: Mapped[str]=mapped_column(String(32),nullable=False,default=Status.PENDING)
    attempt_count: Mapped[int]=mapped_column(Integer,nullable=False,default=0)
    max_attempts: Mapped[int]=mapped_column(Integer,nullable=False)
    next_attempt_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
    lease_until: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    last_error_code: Mapped[str|None]=mapped_column(String(64),nullable=True)
    last_error_message: Mapped[str|None]=mapped_column(Text,nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
    delivered_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)

def utcnow(): return datetime.now(timezone.utc)
