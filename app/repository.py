from datetime import datetime, timezone
from hashlib import sha256
from json import dumps
from uuid import uuid4
from sqlalchemy import and_, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models import NotificationRow, Status, utcnow

class IdempotencyConflict(Exception): pass
class NotFound(Exception): pass

def request_digest(payload: dict) -> str:
    return sha256(dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

class NotificationRepository:
    def __init__(self, session_factory): self.session_factory=session_factory

    def create(self, payload: dict, max_attempts: int) -> NotificationRow:
        digest=request_digest(payload); provider=payload["provider"]; idem=payload.get("idempotency_key")
        with self.session_factory() as s:
            if idem:
                existing=s.scalar(select(NotificationRow).where(NotificationRow.provider==provider,NotificationRow.idempotency_key==idem))
                if existing:
                    if existing.request_digest != digest: raise IdempotencyConflict()
                    return existing
            now=utcnow(); row=NotificationRow(id=f"ntf_{uuid4().hex[:20]}",provider=provider,event_type=payload["event_type"],target_url=payload["target"]["url"],http_method=payload["target"].get("method","POST"),headers_json=payload["target"].get("headers",{}),body_json=payload["target"].get("body",{}),idempotency_key=idem,request_digest=digest,status=Status.PENDING,attempt_count=0,max_attempts=max_attempts,next_attempt_at=now,created_at=now,updated_at=now)
            s.add(row)
            try: s.commit()
            except IntegrityError:
                s.rollback(); raise IdempotencyConflict()
            return row

    def get(self, id: str) -> NotificationRow:
        with self.session_factory() as s:
            row=s.get(NotificationRow,id)
            if not row: raise NotFound()
            return row

    def recover_expired_leases(self, now: datetime) -> int:
        with self.session_factory() as s:
            result=s.execute(update(NotificationRow).where(NotificationRow.status==Status.DELIVERING,NotificationRow.lease_until < now).values(status=Status.RETRY_WAITING,lease_until=None,next_attempt_at=now,updated_at=now));s.commit();return result.rowcount

    def claim_next(self, now: datetime, lease_until: datetime):
        with self.session_factory() as s:
            row=s.scalar(select(NotificationRow).where(NotificationRow.status.in_([Status.PENDING,Status.RETRY_WAITING]),NotificationRow.next_attempt_at<=now).order_by(NotificationRow.created_at).limit(1))
            if not row:return None
            result=s.execute(update(NotificationRow).where(NotificationRow.id==row.id,NotificationRow.status.in_([Status.PENDING,Status.RETRY_WAITING])).values(status=Status.DELIVERING,lease_until=lease_until,updated_at=now));s.commit()
            return self.get(row.id) if result.rowcount==1 else None

    def _update(self,id,attempt,values):
        with self.session_factory() as s:
            values.update(updated_at=utcnow(),lease_until=None)
            result=s.execute(update(NotificationRow).where(NotificationRow.id==id,NotificationRow.status==Status.DELIVERING,NotificationRow.attempt_count==attempt-1).values(**values));s.commit()
            if result.rowcount!=1: raise RuntimeError("notification state conflict")
    def mark_delivered(self,id,attempt,at): self._update(id,attempt,{"status":Status.DELIVERED,"attempt_count":attempt,"delivered_at":at})
    def mark_retry(self,id,attempt,next_attempt_at,code,message): self._update(id,attempt,{"status":Status.RETRY_WAITING,"attempt_count":attempt,"next_attempt_at":next_attempt_at,"last_error_code":code,"last_error_message":message})
    def mark_failed(self,id,attempt,code,message): self._update(id,attempt,{"status":Status.FAILED,"attempt_count":attempt,"last_error_code":code,"last_error_message":message})
